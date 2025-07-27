"""
HTTP API Server Implementation

This module implements an independent HTTP server that provides REST API interfaces
for base64 encoding and decoding operations. The server runs separately from the
MCP transport layer and provides web-friendly endpoints for browser-based clients.

与MCP传输的差异：
- HTTP API服务器提供RESTful接口，而MCP使用JSON-RPC协议
- HTTP API面向Web客户端，MCP面向AI代理
- HTTP API使用标准HTTP状态码，MCP使用协议特定的错误码
- HTTP API支持CORS，便于前端集成
"""

import json
import threading
import os
import mimetypes
import time
from http.server import HTTPServer as BaseHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, Tuple
import logging

from services.base64_service import Base64Service
from services.error_handler import ErrorHandler
from services.logging_service import get_logger, log_request, log_operation, log_error
from services.performance_monitor import record_request, get_performance_monitor


class HTTPAPIRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP API请求处理器
    
    处理REST API请求，提供base64编码解码的HTTP接口。
    支持CORS、JSON请求/响应格式和标准HTTP状态码。
    
    支持的端点：
    - POST /encode: 文本编码为base64
    - POST /decode: base64解码为文本
    - OPTIONS /*: CORS预检请求
    """
    
    def __init__(self, base64_service: Base64Service, *args, **kwargs):
        """
        初始化请求处理器
        
        Args:
            base64_service: Base64服务实例
        """
        self.base64_service = base64_service
        self.error_handler = ErrorHandler()
        self.logger = get_logger(__name__)
        super().__init__(*args, **kwargs)
    
    def do_POST(self) -> None:
        """
        处理POST请求
        
        根据请求路径分发到相应的处理方法：
        - /encode: 处理编码请求
        - /decode: 处理解码请求
        """
        start_time = time.time()
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            if path == '/encode':
                self._handle_encode_request()
            elif path == '/decode':
                self._handle_decode_request()
            else:
                self._send_error_response(404, "Endpoint not found", 
                                        f"Unknown endpoint: {path}")
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_request(
                __name__,
                "POST",
                path=path,
                status_code=500,
                duration_ms=duration_ms,
                client_info={'address': self.client_address[0]},
                extra_data={'error': str(e)}
            )
            log_error(__name__, e, f"Error handling POST request to {path}")
            self._send_error_response(500, "Internal server error", str(e))
    
    def do_OPTIONS(self) -> None:
        """
        处理CORS预检请求
        
        允许跨域访问，支持Web前端调用API。
        这是HTTP API相比MCP传输的重要优势之一。
        """
        self._send_cors_response(200, {})
    
    def do_GET(self) -> None:
        """
        处理GET请求
        
        提供API信息、健康检查端点和静态文件服务。
        """
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            if path == '/health':
                self._handle_health_check()
            elif path == '/api/info':
                self._handle_api_info()
            elif path == '/api/metrics':
                self._handle_metrics_request()
            else:
                # 尝试提供静态文件服务
                self._handle_static_file(path)
                
        except Exception as e:
            self._send_error_response(500, "Internal server error", str(e))
    
    def _handle_encode_request(self) -> None:
        """
        处理编码请求
        
        期望的请求格式：
        {
            "text": "要编码的文本"
        }
        
        响应格式：
        {
            "success": true,
            "result": "编码后的base64字符串"
        }
        """
        start_time = time.time()
        
        try:
            # 读取请求体
            request_data = self._read_json_request()
            
            # 验证请求格式
            if 'text' not in request_data:
                duration_ms = (time.time() - start_time) * 1000
                log_request(
                    __name__,
                    "POST",
                    path="/encode",
                    status_code=400,
                    duration_ms=duration_ms,
                    client_info={'address': self.client_address[0]},
                    extra_data={'error': 'Missing text field'}
                )
                self._send_error_response(400, "Bad request", 
                                        "Missing 'text' field in request")
                return
            
            text = request_data['text']
            
            # 验证文本类型
            if not isinstance(text, str):
                duration_ms = (time.time() - start_time) * 1000
                log_request(
                    __name__,
                    "POST",
                    path="/encode",
                    status_code=400,
                    duration_ms=duration_ms,
                    client_info={'address': self.client_address[0]},
                    extra_data={'error': 'Invalid text type'}
                )
                self._send_error_response(400, "Bad request", 
                                        "'text' field must be a string")
                return
            
            # 执行编码
            try:
                encoded_result = self.base64_service.encode(text)
                
                # 发送成功响应
                response_data = {
                    "success": True,
                    "result": encoded_result
                }
                
                duration_ms = (time.time() - start_time) * 1000
                log_request(
                    __name__,
                    "POST",
                    path="/encode",
                    status_code=200,
                    duration_ms=duration_ms,
                    client_info={'address': self.client_address[0]},
                    extra_data={
                        'input_length': len(text),
                        'output_length': len(encoded_result)
                    }
                )
                
                # 记录性能监控数据
                record_request(
                    "http_encode",
                    duration_ms,
                    True,
                    {
                        'client_ip': self.client_address[0],
                        'input_size_category': self._get_size_category(len(text)),
                        'output_size_category': self._get_size_category(len(encoded_result))
                    }
                )
                
                self._send_json_response(200, response_data)
                
            except ValueError as e:
                # Base64服务抛出的验证错误
                self._send_error_response(400, "Encoding failed", str(e))
                
        except json.JSONDecodeError as e:
            self._send_error_response(400, "Invalid JSON", str(e))
        except Exception as e:
            self._send_error_response(500, "Internal server error", str(e))
    
    def _handle_decode_request(self) -> None:
        """
        处理解码请求
        
        期望的请求格式：
        {
            "base64_string": "要解码的base64字符串"
        }
        
        响应格式：
        {
            "success": true,
            "result": "解码后的文本"
        }
        """
        try:
            # 读取请求体
            request_data = self._read_json_request()
            
            # 验证请求格式
            if 'base64_string' not in request_data:
                self._send_error_response(400, "Bad request", 
                                        "Missing 'base64_string' field in request")
                return
            
            base64_string = request_data['base64_string']
            
            # 验证base64字符串类型
            if not isinstance(base64_string, str):
                self._send_error_response(400, "Bad request", 
                                        "'base64_string' field must be a string")
                return
            
            # 执行解码
            try:
                decoded_result = self.base64_service.decode(base64_string)
                
                # 发送成功响应
                response_data = {
                    "success": True,
                    "result": decoded_result
                }
                self._send_json_response(200, response_data)
                
            except ValueError as e:
                # Base64服务抛出的验证错误
                self._send_error_response(400, "Decoding failed", str(e))
                
        except json.JSONDecodeError as e:
            self._send_error_response(400, "Invalid JSON", str(e))
        except Exception as e:
            self._send_error_response(500, "Internal server error", str(e))
    
    def _handle_health_check(self) -> None:
        """
        处理健康检查请求
        
        返回服务器状态信息，用于监控和负载均衡。
        """
        health_data = {
            "status": "healthy",
            "service": "base64-http-api",
            "version": "1.0.0",
            "endpoints": ["/encode", "/decode", "/health", "/api/info"],
            "static_files": "Enabled"
        }
        self._send_json_response(200, health_data)
    
    def _handle_api_info(self) -> None:
        """
        处理API信息请求
        
        返回API的详细信息和使用说明。
        """
        api_info = {
            "name": "Base64 HTTP API",
            "version": "1.0.0",
            "description": "REST API for base64 encoding and decoding operations",
            "endpoints": {
                "POST /encode": {
                    "description": "Encode text to base64",
                    "request": {"text": "string"},
                    "response": {"success": "boolean", "result": "string"}
                },
                "POST /decode": {
                    "description": "Decode base64 to text",
                    "request": {"base64_string": "string"},
                    "response": {"success": "boolean", "result": "string"}
                },
                "GET /health": {
                    "description": "Health check endpoint",
                    "response": {"status": "string", "service": "string"}
                },
                "GET /api/info": {
                    "description": "API information endpoint",
                    "response": "API documentation object"
                },
                "GET /": {
                    "description": "Web interface for base64 operations",
                    "response": "HTML page"
                },
                "GET /static/*": {
                    "description": "Static file serving (CSS, JS, images)",
                    "response": "Static file content"
                }
            },
            "cors_enabled": True,
            "content_type": "application/json"
        }
        self._send_json_response(200, api_info)
    
    def _handle_metrics_request(self) -> None:
        """
        处理性能监控指标请求
        
        返回服务器性能指标，包括请求统计、系统资源使用情况等。
        """
        try:
            monitor = get_performance_monitor()
            metrics_data = monitor.get_performance_summary()
            
            # 添加HTTP服务器特定信息
            metrics_data['http_server'] = {
                'service_type': 'http_api',
                'endpoints': ['/encode', '/decode', '/health', '/api/info', '/api/metrics'],
                'cors_enabled': True
            }
            
            self._send_json_response(200, metrics_data)
            
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            self._send_error_response(500, "Internal server error", 
                                    f"Failed to get metrics: {str(e)}")
    
    def _handle_static_file(self, path: str) -> None:
        """
        处理静态文件请求
        
        提供静态文件服务，支持HTML、CSS、JavaScript等前端资源。
        实现CORS支持以便前端调用API。
        
        Args:
            path: 请求的文件路径
        """
        # 处理根路径，默认返回index.html
        if path == '/' or path == '':
            path = '/index.html'
        
        # 移除路径前的斜杠
        if path.startswith('/'):
            path = path[1:]
        
        # 安全检查：如果路径包含 ".." 拒绝访问
        if ".." in path:
            self._send_error_response(403, "Forbidden", "Access denied")
            return
        
        # 构建静态文件的完整路径
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        file_path = os.path.join(static_dir, path)
        
        # 安全检查：确保文件路径在static目录内
        try:
            file_path = os.path.abspath(file_path)
            static_dir = os.path.abspath(static_dir)
            
            if not file_path.startswith(static_dir):
                self._send_error_response(403, "Forbidden", "Access denied")
                return
        except Exception:
            self._send_error_response(400, "Bad request", "Invalid file path")
            return
        
        # 检查文件是否存在
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            self._send_error_response(404, "Not found", f"File not found: {path}")
            return
        
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 确定MIME类型
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # 发送响应
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(file_content)))
            
            # 添加缓存控制头部
            if mime_type.startswith('text/') or mime_type.startswith('application/'):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
            else:
                self.send_header('Cache-Control', 'public, max-age=3600')  # 1小时缓存
            
            self.end_headers()
            
            # 写入文件内容
            self.wfile.write(file_content)
            
        except IOError as e:
            self._send_error_response(500, "Internal server error", 
                                    f"Failed to read file: {str(e)}")
        except Exception as e:
            self._send_error_response(500, "Internal server error", 
                                    f"Error serving static file: {str(e)}")
    
    def _read_json_request(self) -> Dict[str, Any]:
        """
        读取并解析JSON请求体
        
        Returns:
            Dict[str, Any]: 解析后的JSON数据
            
        Raises:
            json.JSONDecodeError: JSON格式无效时抛出
        """
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        
        request_body = self.rfile.read(content_length).decode('utf-8')
        return json.loads(request_body)
    
    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """
        发送JSON响应
        
        Args:
            status_code: HTTP状态码
            data: 响应数据
        """
        response_json = json.dumps(data, ensure_ascii=False, indent=2)
        
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_json.encode('utf-8'))))
        self.end_headers()
        
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_cors_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """
        发送CORS响应
        
        Args:
            status_code: HTTP状态码
            data: 响应数据
        """
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()
    
    def _send_error_response(self, status_code: int, error_type: str, message: str) -> None:
        """
        发送错误响应
        
        Args:
            status_code: HTTP状态码
            error_type: 错误类型
            message: 错误消息
        """
        error_data = {
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
                "status_code": status_code
            }
        }
        self._send_json_response(status_code, error_data)
    
    def _send_cors_headers(self) -> None:
        """
        发送CORS头部
        
        允许跨域访问，支持Web前端调用。
        这是HTTP API服务器的重要功能，便于前端集成。
        """
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')  # 24小时
    
    def _get_size_category(self, size: int) -> str:
        """
        Get size category for performance monitoring.
        
        Args:
            size: Size in characters/bytes
            
        Returns:
            Size category string
        """
        if size < 100:
            return "small"
        elif size < 1000:
            return "medium"
        elif size < 10000:
            return "large"
        else:
            return "xlarge"
    
    def setup(self) -> None:
        """Override setup to track connections."""
        super().setup()
        get_performance_monitor().increment_active_connections()
    
    def finish(self) -> None:
        """Override finish to track connections."""
        super().finish()
        get_performance_monitor().decrement_active_connections()
    
    def log_message(self, format: str, *args) -> None:
        """
        重写日志方法
        
        使用标准日志系统记录HTTP请求信息。
        """
        logger = logging.getLogger('http_api_server')
        logger.info(f"{self.address_string()} - {format % args}")


class HTTPServer:
    """
    HTTP API服务器
    
    提供独立的HTTP服务器，与MCP传输层并行运行。
    专门为Web客户端提供RESTful API接口。
    
    与MCP传输的主要差异：
    1. 协议格式：REST API vs JSON-RPC
    2. 目标客户端：Web浏览器 vs AI代理
    3. 错误处理：HTTP状态码 vs MCP错误码
    4. 认证方式：HTTP认证 vs MCP协议认证
    5. 传输方式：HTTP请求/响应 vs 持续连接
    
    特点：
    - 支持CORS跨域访问
    - 标准HTTP状态码
    - JSON请求/响应格式
    - 健康检查端点
    - API信息端点
    """
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        """
        初始化HTTP服务器
        
        Args:
            host: 服务器绑定的主机地址
            port: 服务器监听的端口号
        """
        self.host = host
        self.port = port
        self.base64_service = Base64Service()
        self._server: Optional[BaseHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 配置日志
        self.logger = logging.getLogger('http_api_server')
    
    def start(self) -> None:
        """
        启动HTTP服务器
        
        创建HTTP服务器实例并在后台线程中运行。
        与MCP传输不同，HTTP服务器需要绑定网络端口。
        """
        if self._running:
            self.logger.warning("HTTP server is already running")
            return
        
        try:
            # 创建请求处理器工厂
            def handler_factory(*args, **kwargs):
                return HTTPAPIRequestHandler(self.base64_service, *args, **kwargs)
            
            # 创建HTTP服务器
            self._server = BaseHTTPServer((self.host, self.port), handler_factory)
            
            # 在后台线程中运行服务器
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="HTTPAPIServerThread"
            )
            
            self._running = True
            self._server_thread.start()
            
            self.logger.info(f"HTTP API server started on {self.host}:{self.port}")
            self.logger.info(f"Available endpoints:")
            self.logger.info(f"  POST http://{self.host}:{self.port}/encode")
            self.logger.info(f"  POST http://{self.host}:{self.port}/decode")
            self.logger.info(f"  GET  http://{self.host}:{self.port}/health")
            self.logger.info(f"  GET  http://{self.host}:{self.port}/api/info")
            self.logger.info(f"  GET  http://{self.host}:{self.port}/ (Web Interface)")
            self.logger.info(f"  Static files served from /static/ directory")
            
        except Exception as e:
            self._running = False
            self.logger.error(f"Failed to start HTTP server: {e}")
            raise RuntimeError(f"Failed to start HTTP server: {e}")
    
    def stop(self) -> None:
        """
        停止HTTP服务器
        
        优雅地关闭HTTP服务器，断开所有连接并清理资源。
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._server:
            self.logger.info("Shutting down HTTP API server...")
            self._server.shutdown()
            self._server.server_close()
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
        
        self.logger.info("HTTP API server stopped")
    
    def is_running(self) -> bool:
        """
        检查服务器是否正在运行
        
        Returns:
            bool: 如果服务器正在运行则返回True
        """
        return self._running
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息
        
        Returns:
            dict: 包含服务器状态和配置的信息
        """
        return {
            "server_type": "http_api",
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "base_url": f"http://{self.host}:{self.port}",
            "endpoints": {
                "encode": f"http://{self.host}:{self.port}/encode",
                "decode": f"http://{self.host}:{self.port}/decode",
                "health": f"http://{self.host}:{self.port}/health",
                "api_info": f"http://{self.host}:{self.port}/api/info",
                "web_interface": f"http://{self.host}:{self.port}/",
                "static_files": f"http://{self.host}:{self.port}/static/"
            },
            "methods": ["GET", "POST", "OPTIONS"],
            "cors_enabled": True,
            "content_type": "application/json"
        }
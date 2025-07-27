"""
HTTP Transport Implementation

This module implements HTTP transport for MCP communication.
HTTP transport allows MCP servers to be accessed via HTTP requests,
enabling web-based clients and easier integration with web services.
"""

from typing import Optional, Dict, Any
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from models.mcp_models import MCPRequest, MCPResponse
from .transport_interface import Transport


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    MCP HTTP请求处理器
    
    处理HTTP请求并将其转换为MCP消息格式。支持POST请求用于MCP消息传输，
    同时提供基本的CORS支持以便Web客户端访问。
    """
    
    def __init__(self, transport: 'HTTPTransport', *args, **kwargs):
        """初始化请求处理器"""
        self.transport = transport
        super().__init__(*args, **kwargs)
    
    def do_POST(self) -> None:
        """处理POST请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # 解析JSON请求
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                mcp_request = MCPRequest(
                    jsonrpc=request_data.get('jsonrpc', '2.0'),
                    id=request_data.get('id'),
                    method=request_data.get('method', ''),
                    params=request_data.get('params', {})
                )
                
                # 处理MCP请求
                response = self.transport._handle_request(mcp_request)
                
                # 发送响应
                self._send_json_response(200, response.to_json())
                
            except json.JSONDecodeError as e:
                # JSON解析错误
                from services.error_handler import ErrorHandler
                error_handler = ErrorHandler()
                error = error_handler.create_parse_error(f"Invalid JSON: {e}")
                
                error_response = MCPResponse(error=error)
                self._send_json_response(400, error_response.to_json())
                
        except Exception as e:
            # 处理其他异常
            from services.error_handler import ErrorHandler
            error_handler = ErrorHandler()
            error = error_handler.handle_exception(e, "HTTP request processing error")
            
            error_response = MCPResponse(error=error)
            self._send_json_response(500, error_response.to_json())
    
    def do_OPTIONS(self) -> None:
        """处理CORS预检请求"""
        self._send_cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def _send_json_response(self, status_code: int, json_data: str) -> None:
        """发送JSON响应"""
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_data)))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_cors_headers(self) -> None:
        """发送CORS头部"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def log_message(self, format: str, *args) -> None:
        """重写日志方法以使用标准日志系统"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(format % args)


class HTTPTransport(Transport):
    """
    HTTP传输实现
    
    通过HTTP协议进行MCP消息通信。客户端通过POST请求发送MCP消息，
    服务器在响应中返回MCP结果。
    
    这种传输方式适合Web应用集成和需要通过网络访问的场景。
    """
    
    def __init__(self, host: str = "localhost", port: int = 3000):
        """
        初始化HTTP传输
        
        Args:
            host: 监听的主机地址
            port: 监听的端口号
        """
        super().__init__()
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """
        启动HTTP传输
        
        创建HTTP服务器并在后台线程中运行，监听指定端口上的MCP请求。
        """
        if self._running:
            return
        
        try:
            # 创建HTTP服务器
            def handler_factory(*args, **kwargs):
                return MCPHTTPRequestHandler(self, *args, **kwargs)
            
            self._server = HTTPServer((self.host, self.port), handler_factory)
            
            # 在后台线程中运行服务器
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="HTTPTransportThread"
            )
            
            self._running = True
            self._server_thread.start()
            
        except Exception as e:
            self._running = False
            raise RuntimeError(f"Failed to start HTTP transport: {e}")
    
    def stop(self) -> None:
        """
        停止HTTP传输
        
        关闭HTTP服务器并清理资源。
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
    
    def send_response(self, response: MCPResponse) -> None:
        """
        发送MCP响应
        
        在HTTP传输中，响应是通过HTTP响应直接发送的，
        这个方法主要用于接口一致性。
        
        Args:
            response: MCP响应对象
        """
        # HTTP传输中响应通过HTTP响应直接发送
        # 这个方法主要用于接口一致性
        pass
    
    def get_connection_info(self) -> dict:
        """
        获取HTTP连接信息
        
        Returns:
            dict: 包含传输类型、地址和端口的信息
        """
        return {
            "transport_type": "http",
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}"
        }
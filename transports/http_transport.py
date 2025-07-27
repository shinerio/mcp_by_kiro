"""
HTTP Transport Implementation

This module implements HTTP transport for MCP communication.
HTTP transport allows MCP servers to be accessed via HTTP requests,
enabling web-based clients and easier integration with web services.

与stdio传输的主要差异：
1. 通信模式：HTTP使用请求/响应模式，stdio使用持续的双向流
2. 连接管理：HTTP支持多个并发客户端，stdio通常是单一连接
3. 网络访问：HTTP可以远程访问，stdio限于本地进程通信
4. 协议开销：HTTP有额外的协议头部，stdio更轻量级
5. 状态管理：HTTP是无状态的，stdio可以维持会话状态
6. 错误处理：HTTP可以使用标准HTTP状态码，stdio只能通过MCP错误消息
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
    
    与stdio传输的差异：
    - stdio: 持续监听stdin，逐行处理JSON消息
    - HTTP: 处理单次HTTP请求，解析请求体中的JSON消息
    - stdio: 直接写入stdout发送响应
    - HTTP: 通过HTTP响应头和响应体发送结果
    """
    
    def __init__(self, transport: 'HTTPTransport', *args, **kwargs):
        """初始化请求处理器"""
        self.transport = transport
        super().__init__(*args, **kwargs)
    
    def do_POST(self) -> None:
        """
        处理POST请求
        
        接收MCP消息并通过传输层处理，然后返回响应。
        
        与stdio传输的差异：
        - stdio: 从stdin读取一行JSON消息，立即处理
        - HTTP: 从HTTP请求体读取完整JSON消息，设置适当的HTTP响应
        """
        try:
            # 解析请求路径
            parsed_path = urlparse(self.path)
            
            # 只处理 /mcp 端点
            if parsed_path.path != '/mcp':
                self._send_json_response(404, json.dumps({
                    "error": {
                        "code": 404,
                        "message": "Endpoint not found. Use /mcp for MCP requests."
                    }
                }))
                return
            
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
        """
        处理CORS预检请求
        
        允许Web客户端进行跨域访问，这是HTTP传输相比stdio的优势之一。
        stdio传输无需考虑CORS，因为它不涉及Web浏览器安全策略。
        """
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def _send_json_response(self, status_code: int, json_data: str) -> None:
        """
        发送JSON响应
        
        通过HTTP响应发送MCP消息，包含适当的HTTP头部和状态码。
        与stdio的差异：
        - stdio: 直接写入stdout，以换行符结尾
        - HTTP: 设置HTTP状态码、Content-Type头部，然后写入响应体
        """
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_data)))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_cors_headers(self) -> None:
        """
        发送CORS头部
        
        允许跨域访问，这是HTTP传输为Web客户端提供的重要功能。
        stdio传输无需此功能，因为它不涉及Web浏览器安全限制。
        """
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def log_message(self, format: str, *args) -> None:
        """
        重写日志方法以使用标准日志系统
        
        HTTP传输需要记录更多的连接信息，如客户端IP、请求路径等。
        stdio传输的日志相对简单，主要关注消息处理。
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(format % args)


class HTTPTransport(Transport):
    """
    HTTP传输实现
    
    通过HTTP协议进行MCP消息通信。客户端通过POST请求发送MCP消息，
    服务器在响应中返回MCP结果。
    
    与stdio传输的主要差异：
    
    1. 通信模式：
       - stdio: 持续的双向流通信，客户端和服务器保持连接
       - HTTP: 请求/响应模式，每次交互都是独立的HTTP请求
    
    2. 并发支持：
       - stdio: 通常单一客户端连接
       - HTTP: 支持多个并发客户端连接
    
    3. 网络访问：
       - stdio: 限于本地进程间通信
       - HTTP: 可以通过网络远程访问
    
    4. 状态管理：
       - stdio: 可以维持会话状态
       - HTTP: 无状态，每个请求独立处理
    
    5. 协议开销：
       - stdio: 轻量级，直接JSON消息交换
       - HTTP: 有HTTP头部开销，但提供更多元数据
    
    6. 错误处理：
       - stdio: 只能通过MCP错误消息格式
       - HTTP: 可以使用HTTP状态码 + MCP错误消息
    
    HTTP传输特别适合：
    - Web应用集成
    - 远程MCP服务访问
    - 负载均衡和横向扩展
    - 与现有HTTP基础设施集成
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
        
        与stdio传输的差异：
        - stdio: 直接开始监听stdin，无需网络配置
        - HTTP: 需要绑定网络地址和端口，启动HTTP服务器
        - stdio: 单一输入流处理
        - HTTP: 可以处理多个并发HTTP连接
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
        
        与stdio传输的差异：
        - stdio: 设置停止事件，等待输入线程结束
        - HTTP: 关闭HTTP服务器，断开所有活动连接
        - stdio: 主要是线程同步
        - HTTP: 涉及网络连接管理和资源清理
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
        
        与stdio传输的差异：
        - stdio: 直接写入stdout并刷新缓冲区
        - HTTP: 响应通过HTTP请求处理器在请求上下文中发送
        - stdio: 可以随时发送响应
        - HTTP: 响应必须在HTTP请求处理过程中发送
        
        Args:
            response: MCP响应对象
        """
        # HTTP传输中响应通过HTTP响应直接发送
        # 这个方法主要用于接口一致性
        pass
    
    def get_connection_info(self) -> dict:
        """
        获取HTTP连接信息
        
        返回HTTP传输的详细连接信息，包含网络地址、端点URL等。
        与stdio传输相比，HTTP传输提供更丰富的连接元数据。
        
        Returns:
            dict: 包含传输类型、地址和端口的信息
        """
        return {
            "transport_type": "http",
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "mcp_endpoint": f"http://{self.host}:{self.port}/mcp",
            "methods": ["POST"],
            "cors_enabled": True,
            "description": "HTTP transport for MCP over HTTP protocol"
        }
"""
Transport Layer Interface

This module defines the abstract interface for MCP transport implementations.
Transport layers handle the communication between MCP clients and servers,
abstracting away the underlying communication protocol (stdio, HTTP, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from models.mcp_models import MCPRequest, MCPResponse


class TransportInterface(ABC):
    """
    传输层抽象接口
    
    定义MCP传输层的标准接口。不同的传输实现（stdio、HTTP等）
    必须实现这个接口，确保协议层可以透明地使用不同的传输方式。
    """
    
    @abstractmethod
    def start(self) -> None:
        """
        启动传输层
        
        初始化传输层并开始监听客户端连接。具体行为取决于传输类型：
        - stdio: 开始监听标准输入
        - HTTP: 启动HTTP服务器并监听指定端口
        
        Raises:
            RuntimeError: 当传输层启动失败时抛出
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """
        停止传输层
        
        优雅地关闭传输层，清理资源并断开所有连接。
        
        Raises:
            RuntimeError: 当传输层停止失败时抛出
        """
        pass
    
    @abstractmethod
    def send_response(self, response: MCPResponse) -> None:
        """
        发送MCP响应消息
        
        将MCP响应消息发送给客户端。消息格式和发送方式取决于具体的传输实现。
        
        Args:
            response: 要发送的MCP响应对象
            
        Raises:
            RuntimeError: 当消息发送失败时抛出
        """
        pass
    
    @abstractmethod
    def set_request_handler(self, handler: Callable[[MCPRequest], MCPResponse]) -> None:
        """
        设置请求处理器
        
        注册一个回调函数来处理接收到的MCP请求。传输层接收到请求后
        会调用这个处理器，并将返回的响应发送给客户端。
        
        Args:
            handler: 请求处理函数，接收MCPRequest并返回MCPResponse
        """
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        检查传输层是否正在运行
        
        Returns:
            bool: 如果传输层正在运行则返回True，否则返回False
        """
        pass
    
    @abstractmethod
    def get_connection_info(self) -> dict:
        """
        获取连接信息
        
        返回传输层的连接信息，用于调试和监控。
        
        Returns:
            dict: 包含连接信息的字典，具体内容取决于传输类型
        """
        pass


class Transport(TransportInterface):
    """
    传输层基础实现类
    
    提供传输层接口的基础实现和通用功能。具体的传输类型
    可以继承这个类并重写必要的方法。
    """
    
    def __init__(self):
        """初始化传输层基础组件"""
        self._running = False
        self._request_handler: Optional[Callable[[MCPRequest], MCPResponse]] = None
    
    def set_request_handler(self, handler: Callable[[MCPRequest], MCPResponse]) -> None:
        """设置请求处理器"""
        self._request_handler = handler
    
    def is_running(self) -> bool:
        """检查传输层运行状态"""
        return self._running
    
    def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        内部请求处理方法
        
        调用注册的请求处理器处理请求，如果没有处理器则返回错误响应。
        
        Args:
            request: 接收到的MCP请求
            
        Returns:
            MCPResponse: 处理结果响应
        """
        if self._request_handler is None:
            from services.error_handler import ErrorHandler
            error_handler = ErrorHandler()
            error = error_handler.create_internal_error("No request handler registered")
            return MCPResponse(
                id=request.id,
                error=error
            )
        
        try:
            return self._request_handler(request)
        except Exception as e:
            from services.error_handler import ErrorHandler
            error_handler = ErrorHandler()
            error = error_handler.handle_exception(e, "Request handling failed")
            return MCPResponse(
                id=request.id,
                error=error
            )
    
    def start(self) -> None:
        """启动传输层 - 子类必须实现"""
        raise NotImplementedError("Subclasses must implement start()")
    
    def stop(self) -> None:
        """停止传输层 - 子类必须实现"""
        raise NotImplementedError("Subclasses must implement stop()")
    
    def send_response(self, response: MCPResponse) -> None:
        """发送响应 - 子类必须实现"""
        raise NotImplementedError("Subclasses must implement send_response()")
    
    def get_connection_info(self) -> dict:
        """获取连接信息 - 子类必须实现"""
        raise NotImplementedError("Subclasses must implement get_connection_info()")
"""
Stdio Transport Implementation

This module implements the stdio transport for MCP communication.
Stdio transport uses standard input/output streams for message exchange,
which is the most common transport method for MCP servers.
"""

import sys
import json
import threading
from typing import Optional
from models.mcp_models import MCPRequest, MCPResponse
from .transport_interface import Transport


class StdioTransport(Transport):
    """
    标准输入输出传输实现
    
    通过标准输入输出流进行MCP消息通信。这是MCP协议最常用的传输方式，
    特别适合与AI代理（如Claude）进行集成。
    
    消息格式：每行一个JSON消息，使用换行符分隔。
    """
    
    def __init__(self):
        """初始化stdio传输"""
        super().__init__()
        self._input_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """
        启动stdio传输
        
        开始监听标准输入流中的MCP消息。创建一个后台线程来处理输入，
        避免阻塞主线程。
        """
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        
        # 创建输入处理线程
        self._input_thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="StdioInputThread"
        )
        self._input_thread.start()
    
    def stop(self) -> None:
        """
        停止stdio传输
        
        停止监听标准输入并清理资源。设置停止事件来通知输入线程退出。
        """
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        # 等待输入线程结束
        if self._input_thread and self._input_thread.is_alive():
            self._input_thread.join(timeout=1.0)
    
    def send_response(self, response: MCPResponse) -> None:
        """
        发送MCP响应到标准输出
        
        将响应对象序列化为JSON并写入标准输出流。每个消息占一行，
        以换行符结尾。
        
        Args:
            response: 要发送的MCP响应对象
        """
        if not self._running:
            raise RuntimeError("Transport is not running")
        
        try:
            json_response = response.to_json()
            sys.stdout.write(json_response + "\n")
            sys.stdout.flush()
        except Exception as e:
            raise RuntimeError(f"Failed to send response: {e}")
    
    def get_connection_info(self) -> dict:
        """
        获取stdio连接信息
        
        Returns:
            dict: 包含传输类型和状态的信息
        """
        return {
            "transport_type": "stdio",
            "running": self._running,
            "input_stream": "stdin",
            "output_stream": "stdout"
        }
    
    def _input_loop(self) -> None:
        """
        输入处理循环
        
        在后台线程中运行，持续监听标准输入中的MCP消息。
        解析JSON消息并调用请求处理器。
        """
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # 从标准输入读取一行
                    line = sys.stdin.readline()
                    
                    # 如果读取到EOF，退出循环
                    if not line:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 解析JSON消息
                    try:
                        request = MCPRequest.from_json(line)
                        
                        # 处理请求并发送响应
                        response = self._handle_request(request)
                        self.send_response(response)
                        
                    except json.JSONDecodeError as e:
                        # JSON解析错误，发送错误响应
                        from services.error_handler import ErrorHandler
                        error_handler = ErrorHandler()
                        error = error_handler.create_parse_error(f"Invalid JSON: {e}")
                        
                        error_response = MCPResponse(error=error)
                        self.send_response(error_response)
                        
                except Exception as e:
                    # 处理其他异常
                    from services.error_handler import ErrorHandler
                    error_handler = ErrorHandler()
                    error = error_handler.handle_exception(e, "Input processing error")
                    
                    error_response = MCPResponse(error=error)
                    self.send_response(error_response)
                    
        except Exception as e:
            # 输入循环异常，记录错误但不崩溃
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Stdio input loop error: {e}")
        finally:
            self._running = False
"""
MCP Protocol Handler

This module implements the core MCP (Model Context Protocol) handler that manages
tool registration, request processing, and response generation. It serves as the
bridge between the transport layer and the business logic services.

The handler follows the MCP specification for JSON-RPC 2.0 based communication
and provides standardized tool interfaces for AI agents.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from models.mcp_models import (
    MCPRequest, MCPResponse, MCPError, ToolDefinition, ToolResult,
    MCPMethods, MCPErrorCodes, BASE64_ENCODE_TOOL, BASE64_DECODE_TOOL
)
from services.base64_service import Base64Service
from services.error_handler import ErrorHandler
from services.logging_service import get_logger, log_request, log_operation, log_error
from services.performance_monitor import record_request


class MCPProtocolHandler:
    """
    MCP协议处理器
    
    负责处理MCP协议的核心逻辑，包括工具注册、请求分发和响应生成。
    作为传输层和业务逻辑层之间的桥梁，确保符合MCP规范的通信。
    
    主要功能：
    - 工具注册和管理
    - MCP请求解析和验证
    - 工具调用分发
    - 错误处理和响应生成
    - 日志记录和调试支持
    """
    
    def __init__(self, base64_service: Base64Service):
        """
        初始化MCP协议处理器
        
        Args:
            base64_service: Base64编码解码服务实例
        """
        self.base64_service = base64_service
        self.error_handler = ErrorHandler()
        self.logger = get_logger(__name__)
        
        # 注册可用工具
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_tools()
        
        self.logger.info("MCP Protocol Handler initialized", extra={
            'extra_data': {
                'tools_count': len(self.tools),
                'available_tools': list(self.tools.keys())
            }
        })
        
        self.logger.info(f"MCP Protocol Handler initialized with {len(self.tools)} tools")
    
    def _register_tools(self) -> None:
        """
        注册所有可用的MCP工具
        
        将Base64编码解码工具注册到工具注册表中，使其可以被AI代理发现和调用。
        每个工具都有唯一的名称和详细的输入参数模式定义。
        """
        # 注册base64编码工具
        self.tools[BASE64_ENCODE_TOOL.name] = BASE64_ENCODE_TOOL
        self.logger.debug(f"Registered tool: {BASE64_ENCODE_TOOL.name}")
        
        # 注册base64解码工具
        self.tools[BASE64_DECODE_TOOL.name] = BASE64_DECODE_TOOL
        self.logger.debug(f"Registered tool: {BASE64_DECODE_TOOL.name}")
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        处理MCP请求
        
        根据请求的方法类型分发到相应的处理函数。支持的方法包括：
        - tools/list: 获取可用工具列表
        - tools/call: 调用指定工具
        - initialize: 初始化连接
        - ping: 健康检查
        
        Args:
            request: MCP请求对象
            
        Returns:
            MCPResponse: MCP响应对象，包含结果或错误信息
        """
        start_time = time.time()
        
        try:
            # 验证请求格式
            if not self._validate_request(request):
                duration_ms = (time.time() - start_time) * 1000
                log_request(
                    __name__,
                    request.method,
                    status_code=400,
                    duration_ms=duration_ms,
                    extra_data={'request_id': request.id, 'error': 'Invalid request format'}
                )
                return MCPResponse(
                    id=request.id,
                    error=MCPError(
                        code=MCPErrorCodes.INVALID_REQUEST,
                        message="Invalid request format"
                    )
                )
            
            # 根据方法分发请求
            response = None
            if request.method == MCPMethods.LIST_TOOLS:
                response = self._handle_list_tools(request)
            elif request.method == MCPMethods.CALL_TOOL:
                response = self._handle_call_tool(request)
            elif request.method == MCPMethods.INITIALIZE:
                response = self._handle_initialize(request)
            elif request.method == MCPMethods.PING:
                response = self._handle_ping(request)
            else:
                response = MCPResponse(
                    id=request.id,
                    error=MCPError(
                        code=MCPErrorCodes.METHOD_NOT_FOUND,
                        message=f"Method '{request.method}' not found"
                    )
                )
            
            # 记录请求处理结果
            duration_ms = (time.time() - start_time) * 1000
            status_code = 200 if response.error is None else 400
            success = response.error is None
            
            log_request(
                __name__,
                request.method,
                status_code=status_code,
                duration_ms=duration_ms,
                extra_data={
                    'request_id': request.id,
                    'has_error': response.error is not None,
                    'error_code': response.error.code if response.error else None
                }
            )
            
            # 记录性能监控数据
            record_request(
                f"mcp_{request.method}",
                duration_ms,
                success,
                {
                    'method': request.method,
                    'has_params': bool(request.params),
                    'error_code': str(response.error.code) if response.error else None
                }
            )
            
            return response
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_request(
                __name__,
                request.method,
                status_code=500,
                duration_ms=duration_ms,
                extra_data={'request_id': request.id, 'error': str(e)}
            )
            log_error(__name__, e, f"Error handling MCP request {request.method}", {
                'request_id': request.id,
                'method': request.method
            })
            return MCPResponse(
                id=request.id,
                error=self.error_handler.handle_exception(e)
            )
    
    def _validate_request(self, request: MCPRequest) -> bool:
        """
        验证MCP请求的基本格式
        
        检查请求是否符合JSON-RPC 2.0和MCP规范的基本要求。
        
        Args:
            request: 待验证的MCP请求
            
        Returns:
            bool: 请求是否有效
        """
        # 检查JSON-RPC版本
        if request.jsonrpc != "2.0":
            return False
        
        # 检查方法名称
        if not request.method or not isinstance(request.method, str):
            return False
        
        # 检查参数类型
        if request.params is not None and not isinstance(request.params, dict):
            return False
        
        return True
    
    def _handle_list_tools(self, request: MCPRequest) -> MCPResponse:
        """
        处理工具列表请求
        
        返回所有已注册工具的定义信息，包括工具名称、描述和输入参数模式。
        AI代理使用此信息来了解可用的工具及其使用方法。
        
        Args:
            request: 工具列表请求
            
        Returns:
            MCPResponse: 包含工具列表的响应
        """
        self.logger.debug("Handling list_tools request")
        
        tools_list = [tool.to_dict() for tool in self.tools.values()]
        
        return MCPResponse(
            id=request.id,
            result={
                "tools": tools_list
            }
        )
    
    def _handle_call_tool(self, request: MCPRequest) -> MCPResponse:
        """
        处理工具调用请求
        
        根据请求参数调用指定的工具，并返回执行结果。
        包含完整的参数验证和错误处理。
        
        Args:
            request: 工具调用请求
            
        Returns:
            MCPResponse: 包含工具执行结果的响应
        """
        self.logger.debug(f"Handling call_tool request: {request.params}")
        
        # 验证必需参数
        if "name" not in request.params:
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=MCPErrorCodes.INVALID_PARAMS,
                    message="Missing required parameter: name"
                )
            )
        
        tool_name = request.params["name"]
        arguments = request.params.get("arguments", {})
        
        # 检查工具是否存在
        if tool_name not in self.tools:
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=MCPErrorCodes.TOOL_NOT_FOUND,
                    message=f"Tool '{tool_name}' not found"
                )
            )
        
        try:
            # 调用工具
            result = self._call_tool(tool_name, arguments)
            
            return MCPResponse(
                id=request.id,
                result={
                    "content": result.to_dict()["content"],
                    "isError": result.isError
                }
            )
            
        except ValueError as e:
            # 业务逻辑错误（如无效的base64字符串）
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=MCPErrorCodes.INVALID_PARAMS,
                    message=str(e)
                )
            )
        except Exception as e:
            # 其他未预期的错误
            self.logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            return MCPResponse(
                id=request.id,
                error=self.error_handler.handle_exception(e)
            )
    
    def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """
        处理初始化请求
        
        MCP连接建立时的初始化握手。返回服务器信息和协议版本。
        
        Args:
            request: 初始化请求
            
        Returns:
            MCPResponse: 初始化响应
        """
        self.logger.debug("Handling initialize request")
        
        return MCPResponse(
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mcp-base64-server",
                    "version": "1.0.0"
                }
            }
        )
    
    def _handle_ping(self, request: MCPRequest) -> MCPResponse:
        """
        处理ping请求
        
        简单的健康检查端点，用于验证服务器是否正常运行。
        根据MCP协议规范，ping响应应该是空的或包含简单的确认信息。
        
        Args:
            request: ping请求
            
        Returns:
            MCPResponse: pong响应
        """
        self.logger.debug("Handling ping request")
        
        # According to MCP specification, ping response should be empty or minimal
        return MCPResponse(
            id=request.id,
            result={}
        )
    
    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行具体的工具调用
        
        根据工具名称和参数执行相应的业务逻辑。目前支持：
        - base64_encode: 文本编码为base64
        - base64_decode: base64解码为文本
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            ToolResult: 工具执行结果
            
        Raises:
            ValueError: 参数验证失败或业务逻辑错误
            Exception: 其他执行错误
        """
        self.logger.debug(f"Executing tool: {tool_name} with arguments: {arguments}")
        
        if tool_name == "base64_encode":
            return self._execute_base64_encode(arguments)
        elif tool_name == "base64_decode":
            return self._execute_base64_decode(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _execute_base64_encode(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行base64编码工具
        
        将文本字符串编码为base64格式。包含参数验证和错误处理。
        
        Args:
            arguments: 工具参数，必须包含'text'字段
            
        Returns:
            ToolResult: 编码结果
            
        Raises:
            ValueError: 参数无效或编码失败
        """
        # 验证必需参数
        if "text" not in arguments:
            raise ValueError("Missing required parameter: text")
        
        text = arguments["text"]
        
        # 验证参数类型
        if not isinstance(text, str):
            raise ValueError("Parameter 'text' must be a string")
        
        try:
            # 执行编码
            encoded_result = self.base64_service.encode(text)
            
            self.logger.debug(f"Successfully encoded {len(text)} characters to base64")
            
            return ToolResult(
                content=encoded_result,
                isError=False,
                mimeType="text/plain"
            )
            
        except ValueError as e:
            # Base64Service抛出的验证错误
            self.logger.warning(f"Base64 encoding failed: {str(e)}")
            raise
        except Exception as e:
            # 其他未预期的错误
            self.logger.error(f"Unexpected error in base64 encoding: {str(e)}")
            raise ValueError(f"Encoding failed: {str(e)}")
    
    def _execute_base64_decode(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行base64解码工具
        
        将base64字符串解码为文本。包含格式验证和错误处理。
        
        Args:
            arguments: 工具参数，必须包含'base64_string'字段
            
        Returns:
            ToolResult: 解码结果
            
        Raises:
            ValueError: 参数无效或解码失败
        """
        # 验证必需参数
        if "base64_string" not in arguments:
            raise ValueError("Missing required parameter: base64_string")
        
        base64_string = arguments["base64_string"]
        
        # 验证参数类型
        if not isinstance(base64_string, str):
            raise ValueError("Parameter 'base64_string' must be a string")
        
        try:
            # 执行解码
            decoded_result = self.base64_service.decode(base64_string)
            
            self.logger.debug(f"Successfully decoded base64 string to {len(decoded_result)} characters")
            
            return ToolResult(
                content=decoded_result,
                isError=False,
                mimeType="text/plain"
            )
            
        except ValueError as e:
            # Base64Service抛出的验证错误
            self.logger.warning(f"Base64 decoding failed: {str(e)}")
            raise
        except Exception as e:
            # 其他未预期的错误
            self.logger.error(f"Unexpected error in base64 decoding: {str(e)}")
            raise ValueError(f"Decoding failed: {str(e)}")
    
    def get_available_tools(self) -> List[ToolDefinition]:
        """
        获取所有可用工具的定义
        
        返回当前注册的所有工具定义，用于调试和工具发现。
        
        Returns:
            List[ToolDefinition]: 工具定义列表
        """
        return list(self.tools.values())
    
    def get_tool_count(self) -> int:
        """
        获取已注册工具的数量
        
        Returns:
            int: 工具数量
        """
        return len(self.tools)
"""
Error Handler Service

This module provides unified error handling for the MCP Base64 server.
It standardizes error creation, logging, and response formatting across
different components of the system.
"""

from typing import Dict, Optional, Any
import logging
from models.mcp_models import MCPError, MCPErrorCodes


class ErrorHandler:
    """
    统一错误处理器
    
    提供标准化的错误处理功能，包括错误对象创建、异常处理和日志记录。
    确保整个系统中错误处理的一致性和可维护性。
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化错误处理器
        
        Args:
            logger: 可选的日志记录器，如果未提供则创建默认记录器
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def create_error(self, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> MCPError:
        """
        创建标准化的MCP错误对象
        
        Args:
            code: 错误代码
            message: 错误描述信息
            data: 可选的额外错误数据
            
        Returns:
            MCPError: 标准化的错误对象
        """
        error = MCPError(code=code, message=message, data=data)
        self.logger.error(f"Error created - Code: {code}, Message: {message}, Data: {data}")
        return error
    
    def create_parse_error(self, details: str = "Invalid JSON format") -> MCPError:
        """创建JSON解析错误"""
        return self.create_error(
            code=MCPErrorCodes.PARSE_ERROR,
            message="Parse error",
            data={"details": details}
        )
    
    def create_invalid_request_error(self, details: str = "Invalid request format") -> MCPError:
        """创建无效请求错误"""
        return self.create_error(
            code=MCPErrorCodes.INVALID_REQUEST,
            message="Invalid Request",
            data={"details": details}
        )
    
    def create_method_not_found_error(self, method: str) -> MCPError:
        """创建方法未找到错误"""
        return self.create_error(
            code=MCPErrorCodes.METHOD_NOT_FOUND,
            message="Method not found",
            data={"method": method}
        )
    
    def create_invalid_params_error(self, details: str = "Invalid parameters") -> MCPError:
        """创建无效参数错误"""
        return self.create_error(
            code=MCPErrorCodes.INVALID_PARAMS,
            message="Invalid params",
            data={"details": details}
        )
    
    def create_internal_error(self, details: str = "Internal server error") -> MCPError:
        """创建内部服务器错误"""
        return self.create_error(
            code=MCPErrorCodes.INTERNAL_ERROR,
            message="Internal error",
            data={"details": details}
        )
    
    def create_invalid_base64_error(self, details: str = "Invalid base64 string") -> MCPError:
        """创建无效base64错误"""
        return self.create_error(
            code=MCPErrorCodes.INVALID_BASE64,
            message="Invalid base64 string",
            data={"details": details}
        )
    
    def create_encoding_error(self, details: str = "Encoding failed") -> MCPError:
        """创建编码错误"""
        return self.create_error(
            code=MCPErrorCodes.ENCODING_ERROR,
            message="Encoding error",
            data={"details": details}
        )
    
    def create_decoding_error(self, details: str = "Decoding failed") -> MCPError:
        """创建解码错误"""
        return self.create_error(
            code=MCPErrorCodes.DECODING_ERROR,
            message="Decoding error",
            data={"details": details}
        )
    
    def create_tool_not_found_error(self, tool_name: str) -> MCPError:
        """创建工具未找到错误"""
        return self.create_error(
            code=MCPErrorCodes.TOOL_NOT_FOUND,
            message="Tool not found",
            data={"tool_name": tool_name}
        )
    
    def handle_exception(self, exception: Exception, context: str = "") -> MCPError:
        """
        处理异常并转换为MCP错误
        
        Args:
            exception: 捕获的异常对象
            context: 异常发生的上下文信息
            
        Returns:
            MCPError: 转换后的MCP错误对象
        """
        error_message = f"{context}: {str(exception)}" if context else str(exception)
        self.logger.exception(f"Exception handled: {error_message}")
        
        # 根据异常类型创建相应的错误
        if isinstance(exception, ValueError):
            return self.create_invalid_params_error(error_message)
        elif isinstance(exception, KeyError):
            return self.create_invalid_request_error(error_message)
        elif isinstance(exception, NotImplementedError):
            return self.create_internal_error(f"Feature not implemented: {error_message}")
        elif isinstance(exception, TypeError):
            return self.create_invalid_params_error(f"Type error: {error_message}")
        elif isinstance(exception, AttributeError):
            return self.create_internal_error(f"Attribute error: {error_message}")
        elif isinstance(exception, ImportError):
            return self.create_internal_error(f"Import error: {error_message}")
        elif isinstance(exception, ConnectionError):
            return self.create_internal_error(f"Connection error: {error_message}")
        elif isinstance(exception, TimeoutError):
            return self.create_internal_error(f"Timeout error: {error_message}")
        else:
            return self.create_internal_error(error_message)
    
    def validate_request_format(self, request_data: dict) -> MCPError:
        """
        验证MCP请求格式
        
        Args:
            request_data: 请求数据字典
            
        Returns:
            MCPError: 如果验证失败返回错误对象，否则返回None
        """
        # 检查必需字段
        if not isinstance(request_data, dict):
            return self.create_invalid_request_error("Request must be a JSON object")
        
        if "jsonrpc" not in request_data:
            return self.create_invalid_request_error("Missing 'jsonrpc' field")
        
        if request_data.get("jsonrpc") != "2.0":
            return self.create_invalid_request_error("Invalid 'jsonrpc' version, must be '2.0'")
        
        if "method" not in request_data:
            return self.create_invalid_request_error("Missing 'method' field")
        
        if not isinstance(request_data.get("method"), str):
            return self.create_invalid_request_error("'method' field must be a string")
        
        # 检查可选字段格式
        if "id" in request_data:
            id_value = request_data["id"]
            if not (isinstance(id_value, (str, int)) or id_value is None):
                return self.create_invalid_request_error("'id' field must be string, number, or null")
        
        if "params" in request_data:
            if not isinstance(request_data["params"], dict):
                return self.create_invalid_request_error("'params' field must be an object")
        
        return None
    
    def validate_base64_format(self, base64_string: str) -> MCPError:
        """
        验证base64字符串格式
        
        Args:
            base64_string: 要验证的base64字符串
            
        Returns:
            MCPError: 如果验证失败返回错误对象，否则返回None
        """
        if not isinstance(base64_string, str):
            return self.create_invalid_base64_error("Base64 input must be a string")
        
        if not base64_string.strip():
            return self.create_invalid_base64_error("Base64 string cannot be empty")
        
        # 检查base64字符集
        import re
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
        if not base64_pattern.match(base64_string.replace('\n', '').replace('\r', '').replace(' ', '')):
            return self.create_invalid_base64_error("Base64 string contains invalid characters")
        
        # 检查长度是否为4的倍数（去除空白字符后）
        clean_string = base64_string.replace('\n', '').replace('\r', '').replace(' ', '')
        if len(clean_string) % 4 != 0:
            return self.create_invalid_base64_error("Base64 string length must be a multiple of 4")
        
        return None
    
    def create_http_error_response(self, status_code: int, message: str, details: str = None) -> dict:
        """
        创建HTTP错误响应
        
        Args:
            status_code: HTTP状态码
            message: 错误消息
            details: 详细错误信息
            
        Returns:
            dict: HTTP错误响应字典
        """
        response = {
            "success": False,
            "error": {
                "code": status_code,
                "message": message
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        self.logger.error(f"HTTP Error Response - Status: {status_code}, Message: {message}, Details: {details}")
        
        return response
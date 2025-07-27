"""
MCP Protocol Data Models

This module defines the core data structures for the Model Context Protocol (MCP).
These models represent the standard MCP message format and tool definitions used
for communication between AI agents and MCP servers.

The MCP protocol uses JSON-RPC 2.0 as its underlying message format, with specific
extensions for tool registration and execution.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import json


@dataclass
class MCPRequest:
    """
    MCP请求消息结构
    
    基于JSON-RPC 2.0规范的MCP请求消息。用于客户端向服务器发送工具调用请求、
    工具列表查询等操作。
    
    Attributes:
        jsonrpc: JSON-RPC协议版本，固定为"2.0"
        id: 请求标识符，用于匹配请求和响应
        method: 调用的方法名称（如"tools/list", "tools/call"）
        params: 方法参数字典
    """
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """将请求对象序列化为JSON字符串"""
        return json.dumps({
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPRequest':
        """从JSON字符串反序列化为请求对象"""
        data = json.loads(json_str)
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method", ""),
            params=data.get("params", {})
        )


@dataclass
class MCPError:
    """
    MCP错误信息结构
    
    表示MCP操作中发生的错误。遵循JSON-RPC 2.0错误格式，
    包含标准错误代码和自定义错误信息。
    
    Attributes:
        code: 错误代码（负整数）
        message: 错误描述信息
        data: 可选的额外错误数据
    """
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """将错误对象转换为字典格式"""
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class MCPResponse:
    """
    MCP响应消息结构
    
    MCP服务器对客户端请求的响应消息。包含成功结果或错误信息，
    但不能同时包含两者。
    
    Attributes:
        jsonrpc: JSON-RPC协议版本，固定为"2.0"
        id: 对应请求的标识符
        result: 成功时的结果数据
        error: 失败时的错误信息
    """
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None
    
    def to_json(self) -> str:
        """将响应对象序列化为JSON字符串"""
        response_data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.error is not None:
            response_data["error"] = self.error.to_dict()
        else:
            response_data["result"] = self.result
            
        return json.dumps(response_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """从JSON字符串反序列化为响应对象"""
        data = json.loads(json_str)
        error = None
        if "error" in data:
            error_data = data["error"]
            error = MCPError(
                code=error_data["code"],
                message=error_data["message"],
                data=error_data.get("data")
            )
        
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            result=data.get("result"),
            error=error
        )


@dataclass
class ToolDefinition:
    """
    MCP工具定义结构
    
    定义MCP服务器提供的工具的元数据，包括工具名称、描述和输入参数模式。
    这些信息用于向客户端宣告可用工具及其使用方法。
    
    Attributes:
        name: 工具名称，必须唯一
        description: 工具功能描述
        inputSchema: JSON Schema格式的输入参数定义
    """
    name: str
    description: str
    inputSchema: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """将工具定义转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema
        }


@dataclass
class ToolResult:
    """
    工具执行结果结构
    
    表示MCP工具执行的结果，包含执行状态和结果数据。
    用于向客户端返回工具调用的执行结果。
    
    Attributes:
        content: 工具执行的结果内容
        isError: 是否为错误结果
        mimeType: 结果内容的MIME类型（可选）
    """
    content: str
    isError: bool = False
    mimeType: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """将工具结果转换为字典格式"""
        result = {
            "content": [{"type": "text", "text": self.content}],
            "isError": self.isError
        }
        if self.mimeType:
            result["content"][0]["mimeType"] = self.mimeType
        return result


# MCP协议常量定义
class MCPMethods:
    """MCP协议方法名称常量"""
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    INITIALIZE = "initialize"
    PING = "ping"


class MCPErrorCodes:
    """MCP协议错误代码常量"""
    # JSON-RPC标准错误代码
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP特定错误代码
    INVALID_BASE64 = -1001
    ENCODING_ERROR = -1002
    DECODING_ERROR = -1003
    TOOL_NOT_FOUND = -1004


# Base64工具定义常量
BASE64_ENCODE_TOOL = ToolDefinition(
    name="base64_encode",
    description="将文本字符串编码为base64格式",
    inputSchema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "要编码的文本字符串"
            }
        },
        "required": ["text"]
    }
)

BASE64_DECODE_TOOL = ToolDefinition(
    name="base64_decode", 
    description="将base64字符串解码为文本",
    inputSchema={
        "type": "object",
        "properties": {
            "base64_string": {
                "type": "string",
                "description": "要解码的base64字符串"
            }
        },
        "required": ["base64_string"]
    }
)
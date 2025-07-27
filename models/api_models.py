"""
HTTP API Data Models

This module defines data structures for the HTTP REST API endpoints.
These models are used for request/response serialization in the HTTP server
that runs alongside the MCP server.
"""

from dataclasses import dataclass
from typing import Optional
import json


@dataclass
class EncodeRequest:
    """
    Base64编码请求数据结构
    
    用于HTTP API的编码端点，包含需要编码的文本数据。
    
    Attributes:
        text: 需要编码为base64的文本字符串
    """
    text: str
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EncodeRequest':
        """从JSON字符串创建编码请求对象"""
        data = json.loads(json_str)
        return cls(text=data["text"])
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncodeRequest':
        """从字典创建编码请求对象"""
        return cls(text=data["text"])


@dataclass
class DecodeRequest:
    """
    Base64解码请求数据结构
    
    用于HTTP API的解码端点，包含需要解码的base64字符串。
    
    Attributes:
        base64_string: 需要解码的base64字符串
    """
    base64_string: str
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DecodeRequest':
        """从JSON字符串创建解码请求对象"""
        data = json.loads(json_str)
        return cls(base64_string=data["base64_string"])
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DecodeRequest':
        """从字典创建解码请求对象"""
        return cls(base64_string=data["base64_string"])


@dataclass
class APIResponse:
    """
    HTTP API响应数据结构
    
    统一的API响应格式，用于所有HTTP端点的响应。
    包含操作状态、结果数据和错误信息。
    
    Attributes:
        success: 操作是否成功
        result: 成功时的结果数据
        error: 失败时的错误信息
    """
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    
    def to_json(self) -> str:
        """将响应对象序列化为JSON字符串"""
        response_data = {"success": self.success}
        
        if self.success and self.result is not None:
            response_data["result"] = self.result
        elif not self.success and self.error is not None:
            response_data["error"] = self.error
            
        return json.dumps(response_data)
    
    def to_dict(self) -> dict:
        """将响应对象转换为字典"""
        response_data = {"success": self.success}
        
        if self.success and self.result is not None:
            response_data["result"] = self.result
        elif not self.success and self.error is not None:
            response_data["error"] = self.error
            
        return response_data
    
    @classmethod
    def success_response(cls, result: str) -> 'APIResponse':
        """创建成功响应"""
        return cls(success=True, result=result)
    
    @classmethod
    def error_response(cls, error: str) -> 'APIResponse':
        """创建错误响应"""
        return cls(success=False, error=error)
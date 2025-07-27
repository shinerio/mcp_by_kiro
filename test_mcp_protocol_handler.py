"""
Unit Tests for MCP Protocol Handler

This module contains comprehensive unit tests for the MCPProtocolHandler class,
covering all major functionality including tool registration, request handling,
and error scenarios.
"""

import pytest
import json
from unittest.mock import Mock, patch
from models.mcp_models import (
    MCPRequest, MCPResponse, MCPError, ToolResult,
    MCPMethods, MCPErrorCodes
)
from services.mcp_protocol_handler import MCPProtocolHandler
from services.base64_service import Base64Service


class TestMCPProtocolHandler:
    """MCP协议处理器测试类"""
    
    @pytest.fixture
    def base64_service(self):
        """创建Base64Service实例"""
        return Base64Service()
    
    @pytest.fixture
    def handler(self, base64_service):
        """创建MCPProtocolHandler实例"""
        return MCPProtocolHandler(base64_service)
    
    def test_initialization(self, handler):
        """测试协议处理器初始化"""
        # 验证工具注册
        assert handler.get_tool_count() == 2
        tools = handler.get_available_tools()
        tool_names = [tool.name for tool in tools]
        assert "base64_encode" in tool_names
        assert "base64_decode" in tool_names
    
    def test_handle_list_tools_request(self, handler):
        """测试工具列表请求处理"""
        request = MCPRequest(
            id="test-1",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-1"
        assert response.error is None
        assert "tools" in response.result
        assert len(response.result["tools"]) == 2
        
        # 验证工具定义结构
        tools = response.result["tools"]
        encode_tool = next(t for t in tools if t["name"] == "base64_encode")
        assert encode_tool["description"] == "将文本字符串编码为base64格式"
        assert "inputSchema" in encode_tool
    
    def test_handle_call_tool_encode_success(self, handler):
        """测试成功的base64编码工具调用"""
        request = MCPRequest(
            id="test-2",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": "Hello, World!"}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-2"
        assert response.error is None
        assert response.result["isError"] is False
        
        # 验证编码结果
        content = response.result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "SGVsbG8sIFdvcmxkIQ=="
    
    def test_handle_call_tool_decode_success(self, handler):
        """测试成功的base64解码工具调用"""
        request = MCPRequest(
            id="test-3",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": "SGVsbG8sIFdvcmxkIQ=="}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-3"
        assert response.error is None
        assert response.result["isError"] is False
        
        # 验证解码结果
        content = response.result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Hello, World!"
    
    def test_handle_call_tool_missing_name(self, handler):
        """测试缺少工具名称的调用请求"""
        request = MCPRequest(
            id="test-4",
            method=MCPMethods.CALL_TOOL,
            params={"arguments": {"text": "test"}}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-4"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Missing required parameter: name" in response.error.message
    
    def test_handle_call_tool_unknown_tool(self, handler):
        """测试调用不存在的工具"""
        request = MCPRequest(
            id="test-5",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "unknown_tool",
                "arguments": {}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-5"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.TOOL_NOT_FOUND
        assert "Tool 'unknown_tool' not found" in response.error.message
    
    def test_handle_call_tool_encode_missing_text(self, handler):
        """测试编码工具缺少text参数"""
        request = MCPRequest(
            id="test-6",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-6"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Missing required parameter: text" in response.error.message
    
    def test_handle_call_tool_decode_missing_base64_string(self, handler):
        """测试解码工具缺少base64_string参数"""
        request = MCPRequest(
            id="test-7",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-7"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Missing required parameter: base64_string" in response.error.message
    
    def test_handle_call_tool_decode_invalid_base64(self, handler):
        """测试解码无效的base64字符串"""
        request = MCPRequest(
            id="test-8",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": "invalid-base64!"}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-8"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Invalid base64 input" in response.error.message
    
    def test_handle_call_tool_encode_invalid_text_type(self, handler):
        """测试编码工具接收非字符串类型参数"""
        request = MCPRequest(
            id="test-9",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": 123}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-9"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Parameter 'text' must be a string" in response.error.message
    
    def test_handle_call_tool_decode_invalid_base64_type(self, handler):
        """测试解码工具接收非字符串类型参数"""
        request = MCPRequest(
            id="test-10",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": 123}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-10"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Parameter 'base64_string' must be a string" in response.error.message
    
    def test_handle_initialize_request(self, handler):
        """测试初始化请求处理"""
        request = MCPRequest(
            id="test-11",
            method=MCPMethods.INITIALIZE,
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-11"
        assert response.error is None
        assert "protocolVersion" in response.result
        assert "capabilities" in response.result
        assert "serverInfo" in response.result
        assert response.result["serverInfo"]["name"] == "mcp-base64-server"
    
    def test_handle_ping_request(self, handler):
        """测试ping请求处理"""
        request = MCPRequest(
            id="test-12",
            method=MCPMethods.PING,
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-12"
        assert response.error is None
        assert response.result["status"] == "pong"
    
    def test_handle_unknown_method(self, handler):
        """测试未知方法请求"""
        request = MCPRequest(
            id="test-13",
            method="unknown_method",
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-13"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.METHOD_NOT_FOUND
        assert "Method 'unknown_method' not found" in response.error.message
    
    def test_handle_invalid_request_format(self, handler):
        """测试无效的请求格式"""
        # 测试无效的JSON-RPC版本
        request = MCPRequest(
            id="test-14",
            jsonrpc="1.0",  # 无效版本
            method=MCPMethods.PING,
            params={}
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-14"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_REQUEST
        assert "Invalid request format" in response.error.message
    
    def test_handle_request_with_exception(self, handler):
        """测试请求处理过程中发生异常"""
        # 模拟Base64Service抛出异常
        with patch.object(handler.base64_service, 'encode', side_effect=Exception("Unexpected error")):
            request = MCPRequest(
                id="test-15",
                method=MCPMethods.CALL_TOOL,
                params={
                    "name": "base64_encode",
                    "arguments": {"text": "test"}
                }
            )
            
            response = handler.handle_request(request)
            
            assert response.id == "test-15"
            assert response.error is not None
            # The exception is caught and re-raised as ValueError, resulting in INVALID_PARAMS
            assert response.error.code == MCPErrorCodes.INVALID_PARAMS
            assert "Encoding failed: Unexpected error" in response.error.message
    
    def test_empty_text_encoding(self, handler):
        """测试空字符串编码"""
        request = MCPRequest(
            id="test-16",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": ""}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-16"
        assert response.error is None
        assert response.result["isError"] is False
        
        # 空字符串的base64编码应该是空字符串
        content = response.result["content"]
        assert content[0]["text"] == ""
    
    def test_empty_base64_decoding(self, handler):
        """测试空base64字符串解码"""
        request = MCPRequest(
            id="test-17",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": ""}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-17"
        assert response.error is not None
        assert response.error.code == MCPErrorCodes.INVALID_PARAMS
        assert "Base64 string cannot be empty" in response.error.message
    
    def test_unicode_text_encoding(self, handler):
        """测试Unicode文本编码"""
        unicode_text = "你好，世界！🌍"
        request = MCPRequest(
            id="test-18",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": unicode_text}
            }
        )
        
        response = handler.handle_request(request)
        
        assert response.id == "test-18"
        assert response.error is None
        assert response.result["isError"] is False
        
        # 验证可以正确编码Unicode文本
        content = response.result["content"]
        encoded_result = content[0]["text"]
        assert len(encoded_result) > 0
        
        # 验证可以正确解码回原文本
        decode_request = MCPRequest(
            id="test-19",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": encoded_result}
            }
        )
        
        decode_response = handler.handle_request(decode_request)
        assert decode_response.error is None
        decoded_content = decode_response.result["content"]
        assert decoded_content[0]["text"] == unicode_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
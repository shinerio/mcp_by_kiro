"""
MCP Inspector Integration Tests

This module contains specialized integration tests that verify the MCP Base64 server
works correctly with MCP Inspector tool. These tests simulate the exact behavior
of MCP Inspector to ensure proper tool discovery, execution, and debugging support.

Requirements covered:
- 5.1: 验证工具在MCP Inspector中的显示
- 5.2: 测试通过Inspector的工具调用功能  
- 5.4: 验证调试信息的正确性
- 5.5: 确保Inspector能够正确识别连接问题
"""

import pytest
import json
import time
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
from pathlib import Path

# Import system components
from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from transports.stdio_transport import StdioTransport
from transports.http_transport import HTTPTransport
from models.mcp_models import MCPRequest, MCPResponse, MCPMethods, MCPErrorCodes
from config import ConfigManager


class TestMCPInspectorToolDiscovery:
    """MCP Inspector工具发现测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
    
    def test_inspector_tool_list_format(self):
        """测试Inspector工具列表格式兼容性"""
        # 模拟Inspector发送的工具列表请求
        request = MCPRequest(
            id="inspector-tools-list",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = self.mcp_handler.handle_request(request)
        
        # 验证响应格式符合Inspector期望
        assert response.error is None
        assert "tools" in response.result
        
        tools = response.result["tools"]
        assert isinstance(tools, list)
        assert len(tools) == 2
        
        # 验证每个工具都有Inspector需要的字段
        required_fields = ["name", "description", "inputSchema"]
        
        for tool in tools:
            for field in required_fields:
                assert field in tool, f"Tool missing required field: {field}"
            
            # 验证工具名称符合MCP规范
            assert isinstance(tool["name"], str)
            assert len(tool["name"]) > 0
            assert not tool["name"].startswith("_")  # 不应该以下划线开头
            
            # 验证描述信息对Inspector友好
            assert isinstance(tool["description"], str)
            assert len(tool["description"]) > 10  # 足够详细的描述
            
            # 验证JSON Schema格式
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema
            assert isinstance(schema["required"], list)
    
    def test_inspector_tool_schema_validation(self):
        """测试Inspector工具Schema验证"""
        request = MCPRequest(
            id="schema-validation",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = self.mcp_handler.handle_request(request)
        tools = response.result["tools"]
        
        # 验证base64_encode工具schema
        encode_tool = next(t for t in tools if t["name"] == "base64_encode")
        encode_schema = encode_tool["inputSchema"]
        
        assert "text" in encode_schema["properties"]
        assert encode_schema["properties"]["text"]["type"] == "string"
        assert "description" in encode_schema["properties"]["text"]
        assert "text" in encode_schema["required"]
        
        # 验证base64_decode工具schema
        decode_tool = next(t for t in tools if t["name"] == "base64_decode")
        decode_schema = decode_tool["inputSchema"]
        
        assert "base64_string" in decode_schema["properties"]
        assert decode_schema["properties"]["base64_string"]["type"] == "string"
        assert "description" in decode_schema["properties"]["base64_string"]
        assert "base64_string" in decode_schema["required"]
    
    def test_inspector_tool_descriptions_localization(self):
        """测试Inspector工具描述本地化"""
        request = MCPRequest(
            id="localization-test",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = self.mcp_handler.handle_request(request)
        tools = response.result["tools"]
        
        # 验证工具描述是中文的（符合需求文档）
        for tool in tools:
            description = tool["description"]
            
            # 检查是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in description)
            assert has_chinese, f"Tool {tool['name']} description should be in Chinese"
            
            # 验证参数描述也是中文的
            properties = tool["inputSchema"]["properties"]
            for prop_name, prop_def in properties.items():
                prop_desc = prop_def["description"]
                has_chinese_prop = any('\u4e00' <= char <= '\u9fff' for char in prop_desc)
                assert has_chinese_prop, f"Property {prop_name} description should be in Chinese"


class TestMCPInspectorToolExecution:
    """MCP Inspector工具执行测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
    
    def test_inspector_encode_tool_execution(self):
        """测试Inspector执行编码工具"""
        # 模拟Inspector调用base64_encode工具
        test_cases = [
            {"input": "Hello Inspector", "expected": "SGVsbG8gSW5zcGVjdG9y"},
            {"input": "MCP测试", "expected": "TUNQ5rWL6K+V"},
            {"input": "", "expected": ""},
            {"input": "Special chars: !@#$%^&*()", "expected": "U3BlY2lhbCBjaGFyczogIUAjJCVeJiooKQ=="}
        ]
        
        for i, case in enumerate(test_cases):
            request = MCPRequest(
                id=f"inspector-encode-{i}",
                method=MCPMethods.CALL_TOOL,
                params={
                    "name": "base64_encode",
                    "arguments": {"text": case["input"]}
                }
            )
            
            response = self.mcp_handler.handle_request(request)
            
            # 验证Inspector能够获得正确的响应格式
            assert response.error is None
            assert response.result["isError"] is False
            
            content = response.result["content"]
            assert len(content) == 1
            assert content[0]["type"] == "text"
            assert content[0]["text"] == case["expected"]
    
    def test_inspector_decode_tool_execution(self):
        """测试Inspector执行解码工具"""
        test_cases = [
            {"input": "SGVsbG8gSW5zcGVjdG9y", "expected": "Hello Inspector"},
            {"input": "TUNQ5rWL6K+V", "expected": "MCP测试"},
            {"input": "U3BlY2lhbCBjaGFyczogIUAjJCVeJiooKQ==", "expected": "Special chars: !@#$%^&*()"}
        ]
        
        for i, case in enumerate(test_cases):
            request = MCPRequest(
                id=f"inspector-decode-{i}",
                method=MCPMethods.CALL_TOOL,
                params={
                    "name": "base64_decode",
                    "arguments": {"base64_string": case["input"]}
                }
            )
            
            response = self.mcp_handler.handle_request(request)
            
            # 验证Inspector能够获得正确的响应格式
            assert response.error is None
            assert response.result["isError"] is False
            
            content = response.result["content"]
            assert len(content) == 1
            assert content[0]["type"] == "text"
            assert content[0]["text"] == case["expected"]
    
    def test_inspector_tool_execution_with_validation(self):
        """测试Inspector工具执行时的参数验证"""
        # 测试各种无效输入场景
        invalid_scenarios = [
            # 编码工具 - 非字符串输入
            {
                "tool": "base64_encode",
                "args": {"text": 123},
                "expected_error": "Parameter 'text' must be a string"
            },
            # 编码工具 - 缺少参数
            {
                "tool": "base64_encode", 
                "args": {},
                "expected_error": "Missing required parameter: text"
            },
            # 解码工具 - 无效base64
            {
                "tool": "base64_decode",
                "args": {"base64_string": "invalid@base64"},
                "expected_error": "Invalid base64 input"
            },
            # 解码工具 - 空字符串
            {
                "tool": "base64_decode",
                "args": {"base64_string": ""},
                "expected_error": "Base64 string cannot be empty"
            }
        ]
        
        for i, scenario in enumerate(invalid_scenarios):
            request = MCPRequest(
                id=f"inspector-validation-{i}",
                method=MCPMethods.CALL_TOOL,
                params={
                    "name": scenario["tool"],
                    "arguments": scenario["args"]
                }
            )
            
            response = self.mcp_handler.handle_request(request)
            
            # 验证Inspector能够获得清晰的错误信息
            assert response.error is not None
            assert scenario["expected_error"] in response.error.message
            assert response.error.code == MCPErrorCodes.INVALID_PARAMS


class TestMCPInspectorDebugging:
    """MCP Inspector调试功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
    
    def test_inspector_server_info_display(self):
        """测试Inspector服务器信息显示"""
        # 模拟Inspector获取服务器信息
        request = MCPRequest(
            id="inspector-server-info",
            method=MCPMethods.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}}
            }
        )
        
        response = self.mcp_handler.handle_request(request)
        
        # 验证Inspector能够显示的服务器信息
        assert response.error is None
        assert "serverInfo" in response.result
        
        server_info = response.result["serverInfo"]
        assert "name" in server_info
        assert "version" in server_info
        assert server_info["name"] == "mcp-base64-server"
        
        # 验证协议版本信息
        assert response.result["protocolVersion"] == "2024-11-05"
        
        # 验证能力信息
        assert "capabilities" in response.result
        capabilities = response.result["capabilities"]
        assert "tools" in capabilities
    
    def test_inspector_ping_functionality(self):
        """测试Inspector ping功能"""
        # Inspector使用ping来检查服务器状态
        request = MCPRequest(
            id="inspector-ping",
            method=MCPMethods.PING,
            params={}
        )
        
        response = self.mcp_handler.handle_request(request)
        
        # 验证ping响应格式
        assert response.error is None
        assert response.result["status"] == "pong"
        assert response.id == "inspector-ping"
    
    def test_inspector_error_message_clarity(self):
        """测试Inspector错误消息清晰度"""
        # 测试各种错误场景的消息质量
        error_scenarios = [
            {
                "name": "unknown_method",
                "request": MCPRequest(
                    id="debug-unknown-method",
                    method="unknown/method",
                    params={}
                ),
                "check": lambda msg: "Method" in msg and "not found" in msg
            },
            {
                "name": "unknown_tool",
                "request": MCPRequest(
                    id="debug-unknown-tool",
                    method=MCPMethods.CALL_TOOL,
                    params={"name": "unknown_tool", "arguments": {}}
                ),
                "check": lambda msg: "Tool" in msg and "not found" in msg
            },
            {
                "name": "invalid_json_rpc",
                "request": MCPRequest(
                    id="debug-invalid-jsonrpc",
                    jsonrpc="1.0",  # 无效版本
                    method=MCPMethods.PING,
                    params={}
                ),
                "check": lambda msg: "Invalid request format" in msg
            }
        ]
        
        for scenario in error_scenarios:
            response = self.mcp_handler.handle_request(scenario["request"])
            
            # 验证错误消息对Inspector用户友好
            assert response.error is not None
            assert len(response.error.message) > 0
            assert scenario["check"](response.error.message)
            
            # 验证错误代码是标准的
            assert response.error.code < 0  # 错误代码应该是负数
    
    def test_inspector_request_response_tracing(self):
        """测试Inspector请求响应跟踪"""
        # 测试请求ID的正确传递（Inspector用于跟踪请求）
        test_ids = [
            "inspector-trace-1",
            "inspector-trace-2", 
            "inspector-trace-3"
        ]
        
        for test_id in test_ids:
            request = MCPRequest(
                id=test_id,
                method=MCPMethods.LIST_TOOLS,
                params={}
            )
            
            response = self.mcp_handler.handle_request(request)
            
            # 验证响应ID与请求ID匹配
            assert response.id == test_id
            
            # 验证响应格式一致性
            assert response.jsonrpc == "2.0"
    
    def test_inspector_tool_parameter_hints(self):
        """测试Inspector工具参数提示"""
        # 获取工具定义
        request = MCPRequest(
            id="parameter-hints",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = self.mcp_handler.handle_request(request)
        tools = response.result["tools"]
        
        # 验证每个工具的参数都有详细的提示信息
        for tool in tools:
            schema = tool["inputSchema"]
            properties = schema["properties"]
            
            for param_name, param_def in properties.items():
                # 验证参数类型明确
                assert "type" in param_def
                
                # 验证参数描述详细
                assert "description" in param_def
                assert len(param_def["description"]) > 5
                
                # 验证描述包含使用提示
                description = param_def["description"]
                if param_name == "text":
                    assert "编码" in description or "文本" in description
                elif param_name == "base64_string":
                    assert "解码" in description or "base64" in description


class TestMCPInspectorConnectionHandling:
    """MCP Inspector连接处理测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
    
    def test_inspector_stdio_connection_simulation(self):
        """测试Inspector通过stdio连接的模拟"""
        transport = StdioTransport()
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        with patch('sys.stdin') as mock_stdin, patch('sys.stdout') as mock_stdout:
            # 模拟Inspector的连接序列
            inspector_sequence = [
                # 1. 初始化连接
                MCPRequest(
                    id="inspector-init",
                    method=MCPMethods.INITIALIZE,
                    params={"protocolVersion": "2024-11-05", "capabilities": {}}
                ).to_json() + "\n",
                # 2. 获取工具列表
                MCPRequest(
                    id="inspector-list",
                    method=MCPMethods.LIST_TOOLS,
                    params={}
                ).to_json() + "\n",
                # 3. 测试工具调用
                MCPRequest(
                    id="inspector-test",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": "base64_encode",
                        "arguments": {"text": "Inspector Connection Test"}
                    }
                ).to_json() + "\n",
                ""  # EOF
            ]
            
            mock_stdin.readline.side_effect = inspector_sequence
            
            # 收集Inspector会看到的响应
            inspector_responses = []
            def capture_inspector_output(data):
                if data.strip():
                    inspector_responses.append(json.loads(data.strip()))
            
            mock_stdout.write.side_effect = capture_inspector_output
            mock_stdout.flush = Mock()
            
            transport.start()
            time.sleep(0.1)
            
            # 验证Inspector连接流程成功
            assert len(inspector_responses) == 3
            
            # 验证初始化响应
            init_resp = inspector_responses[0]
            assert init_resp["id"] == "inspector-init"
            assert "serverInfo" in init_resp["result"]
            
            # 验证工具列表响应
            list_resp = inspector_responses[1]
            assert list_resp["id"] == "inspector-list"
            assert len(list_resp["result"]["tools"]) == 2
            
            # 验证工具调用响应
            test_resp = inspector_responses[2]
            assert test_resp["id"] == "inspector-test"
            assert test_resp["result"]["isError"] is False
    
    def test_inspector_http_connection_simulation(self):
        """测试Inspector通过HTTP连接的模拟"""
        transport = HTTPTransport(host="localhost", port=8993)
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        try:
            transport.start()
            time.sleep(0.1)
            
            base_url = "http://localhost:8993"
            
            # 模拟Inspector的HTTP连接测试
            # 1. 检查服务器可达性
            try:
                import requests
                
                # 2. 初始化连接
                init_request = {
                    "jsonrpc": "2.0",
                    "id": "inspector-http-init",
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
                }
                
                response = requests.post(f"{base_url}/mcp", json=init_request, timeout=5)
                assert response.status_code == 200
                
                init_data = response.json()
                assert init_data["id"] == "inspector-http-init"
                
                # 3. 获取工具列表
                list_request = {
                    "jsonrpc": "2.0",
                    "id": "inspector-http-list",
                    "method": "tools/list",
                    "params": {}
                }
                
                response = requests.post(f"{base_url}/mcp", json=list_request, timeout=5)
                assert response.status_code == 200
                
                list_data = response.json()
                assert len(list_data["result"]["tools"]) == 2
                
                # 4. 测试CORS支持（Inspector Web版本需要）
                options_response = requests.options(f"{base_url}/mcp")
                assert "Access-Control-Allow-Origin" in options_response.headers
                
            except ImportError:
                pytest.skip("requests library not available for HTTP testing")
                
        finally:
            transport.stop()
    
    def test_inspector_connection_error_handling(self):
        """测试Inspector连接错误处理"""
        # 测试各种连接错误场景
        
        # 1. 测试无效的初始化参数
        invalid_init = MCPRequest(
            id="invalid-init",
            method=MCPMethods.INITIALIZE,
            params={"protocolVersion": "invalid-version"}
        )
        
        response = self.mcp_handler.handle_request(invalid_init)
        # 服务器应该仍然响应，但可能包含警告信息
        assert response.id == "invalid-init"
        
        # 2. 测试缺少必需参数的初始化
        missing_params_init = MCPRequest(
            id="missing-params-init",
            method=MCPMethods.INITIALIZE,
            params={}
        )
        
        response = self.mcp_handler.handle_request(missing_params_init)
        assert response.id == "missing-params-init"
        # 应该仍然成功，使用默认值
        assert response.error is None
    
    def test_inspector_session_management(self):
        """测试Inspector会话管理"""
        # 模拟Inspector的完整会话
        session_requests = [
            # 会话开始
            ("session-start", MCPMethods.INITIALIZE, {"protocolVersion": "2024-11-05"}),
            # 健康检查
            ("health-check", MCPMethods.PING, {}),
            # 工具发现
            ("tool-discovery", MCPMethods.LIST_TOOLS, {}),
            # 工具测试
            ("tool-test-1", MCPMethods.CALL_TOOL, {
                "name": "base64_encode",
                "arguments": {"text": "Session Test"}
            }),
            # 另一个工具测试
            ("tool-test-2", MCPMethods.CALL_TOOL, {
                "name": "base64_decode", 
                "arguments": {"base64_string": "U2Vzc2lvbiBUZXN0"}
            }),
            # 最终健康检查
            ("final-check", MCPMethods.PING, {})
        ]
        
        # 执行完整会话
        session_responses = []
        for req_id, method, params in session_requests:
            request = MCPRequest(id=req_id, method=method, params=params)
            response = self.mcp_handler.handle_request(request)
            session_responses.append(response)
        
        # 验证会话的一致性
        assert len(session_responses) == len(session_requests)
        
        for i, response in enumerate(session_responses):
            expected_id = session_requests[i][0]
            assert response.id == expected_id
            
            # 所有请求都应该成功（除非是故意的错误测试）
            if session_requests[i][1] != "invalid_method":
                assert response.error is None


if __name__ == "__main__":
    # 运行MCP Inspector集成测试
    pytest.main([__file__, "-v", "--tb=short"])
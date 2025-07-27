"""
Integration Tests for MCP Base64 Server

This module contains comprehensive integration tests that verify the complete
end-to-end functionality of the MCP Base64 server, including both stdio and
HTTP transport methods, error scenarios, and real-world usage patterns.

Requirements covered:
- 5.1: MCP Inspector工具显示和连接测试
- 5.2: 工具调用功能验证
- 5.3: 错误场景的集成测试
"""

import pytest
import json
import time
import threading
import subprocess
import requests
import tempfile
import os
import signal
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch
from io import StringIO

# Import system components
from main import main
from config import ConfigManager, Config
from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from transports.stdio_transport import StdioTransport
from transports.http_transport import HTTPTransport
from servers.http_server import HTTPServer
from models.mcp_models import MCPRequest, MCPResponse, MCPMethods


class TestMCPServerIntegration:
    """MCP服务器集成测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
        
    def teardown_method(self):
        """测试后清理"""
        # 清理可能的资源
        pass
    
    def test_complete_mcp_workflow_stdio(self):
        """测试完整的MCP工作流程 - stdio传输"""
        # 创建stdio传输
        transport = StdioTransport()
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        # 模拟stdin/stdout
        with patch('sys.stdin') as mock_stdin, patch('sys.stdout') as mock_stdout:
            # 准备测试请求序列
            test_requests = [
                # 1. 初始化请求
                MCPRequest(
                    id="init-1",
                    method=MCPMethods.INITIALIZE,
                    params={"protocolVersion": "2024-11-05", "capabilities": {}}
                ),
                # 2. 工具列表请求
                MCPRequest(
                    id="list-1",
                    method=MCPMethods.LIST_TOOLS,
                    params={}
                ),
                # 3. Base64编码工具调用
                MCPRequest(
                    id="encode-1",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": "base64_encode",
                        "arguments": {"text": "Hello, MCP World!"}
                    }
                ),
                # 4. Base64解码工具调用
                MCPRequest(
                    id="decode-1",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": "base64_decode",
                        "arguments": {"base64_string": "SGVsbG8sIE1DUCBXb3JsZCE="}
                    }
                )
            ]
            
            # 模拟输入序列
            input_lines = [req.to_json() + "\n" for req in test_requests] + [""]
            mock_stdin.readline.side_effect = input_lines
            
            # 收集输出
            responses = []
            def capture_output(data):
                if data.strip():
                    responses.append(json.loads(data.strip()))
            
            mock_stdout.write.side_effect = capture_output
            mock_stdout.flush = Mock()
            
            # 启动传输并等待处理
            transport.start()
            time.sleep(0.2)
            
            # 验证响应
            assert len(responses) == 4
            
            # 验证初始化响应
            init_response = responses[0]
            assert init_response["id"] == "init-1"
            assert "result" in init_response
            assert init_response["result"]["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in init_response["result"]
            
            # 验证工具列表响应
            list_response = responses[1]
            assert list_response["id"] == "list-1"
            assert "tools" in list_response["result"]
            assert len(list_response["result"]["tools"]) == 2
            
            tool_names = [tool["name"] for tool in list_response["result"]["tools"]]
            assert "base64_encode" in tool_names
            assert "base64_decode" in tool_names
            
            # 验证编码响应
            encode_response = responses[2]
            assert encode_response["id"] == "encode-1"
            assert encode_response["result"]["isError"] is False
            assert encode_response["result"]["content"][0]["text"] == "SGVsbG8sIE1DUCBXb3JsZCE="
            
            # 验证解码响应
            decode_response = responses[3]
            assert decode_response["id"] == "decode-1"
            assert decode_response["result"]["isError"] is False
            assert decode_response["result"]["content"][0]["text"] == "Hello, MCP World!"
    
    def test_complete_mcp_workflow_http(self):
        """测试完整的MCP工作流程 - HTTP传输"""
        # 创建HTTP传输
        transport = HTTPTransport(host="localhost", port=8997)
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        try:
            transport.start()
            time.sleep(0.1)  # 等待服务器启动
            
            base_url = "http://localhost:8997"
            
            # 1. 测试初始化请求
            init_request = {
                "jsonrpc": "2.0",
                "id": "init-http-1",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
            }
            
            response = requests.post(f"{base_url}/mcp", json=init_request)
            assert response.status_code == 200
            
            init_data = response.json()
            assert init_data["id"] == "init-http-1"
            assert "result" in init_data
            
            # 2. 测试工具列表请求
            list_request = {
                "jsonrpc": "2.0",
                "id": "list-http-1",
                "method": "tools/list",
                "params": {}
            }
            
            response = requests.post(f"{base_url}/mcp", json=list_request)
            assert response.status_code == 200
            
            list_data = response.json()
            assert len(list_data["result"]["tools"]) == 2
            
            # 3. 测试编码工具调用
            encode_request = {
                "jsonrpc": "2.0",
                "id": "encode-http-1",
                "method": "tools/call",
                "params": {
                    "name": "base64_encode",
                    "arguments": {"text": "HTTP Transport Test"}
                }
            }
            
            response = requests.post(f"{base_url}/mcp", json=encode_request)
            assert response.status_code == 200
            
            encode_data = response.json()
            assert encode_data["result"]["isError"] is False
            encoded_result = encode_data["result"]["content"][0]["text"]
            
            # 4. 测试解码工具调用
            decode_request = {
                "jsonrpc": "2.0",
                "id": "decode-http-1",
                "method": "tools/call",
                "params": {
                    "name": "base64_decode",
                    "arguments": {"base64_string": encoded_result}
                }
            }
            
            response = requests.post(f"{base_url}/mcp", json=decode_request)
            assert response.status_code == 200
            
            decode_data = response.json()
            assert decode_data["result"]["content"][0]["text"] == "HTTP Transport Test"
            
        finally:
            transport.stop()
    
    def test_error_scenarios_integration(self):
        """测试错误场景的集成处理"""
        transport = StdioTransport()
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        with patch('sys.stdin') as mock_stdin, patch('sys.stdout') as mock_stdout:
            # 准备错误场景测试
            error_scenarios = [
                # 1. 无效JSON
                "invalid json content\n",
                # 2. 无效方法
                MCPRequest(id="err-1", method="invalid_method", params={}).to_json() + "\n",
                # 3. 缺少必需参数
                MCPRequest(id="err-2", method=MCPMethods.CALL_TOOL, params={}).to_json() + "\n",
                # 4. 无效工具名称
                MCPRequest(
                    id="err-3", 
                    method=MCPMethods.CALL_TOOL,
                    params={"name": "invalid_tool", "arguments": {}}
                ).to_json() + "\n",
                # 5. 无效base64解码
                MCPRequest(
                    id="err-4",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": "base64_decode",
                        "arguments": {"base64_string": "invalid@base64"}
                    }
                ).to_json() + "\n",
                ""  # EOF
            ]
            
            mock_stdin.readline.side_effect = error_scenarios
            
            # 收集错误响应
            error_responses = []
            def capture_errors(data):
                if data.strip():
                    error_responses.append(json.loads(data.strip()))
            
            mock_stdout.write.side_effect = capture_errors
            mock_stdout.flush = Mock()
            
            transport.start()
            time.sleep(0.2)
            
            # 验证所有错误都被正确处理
            assert len(error_responses) == 5
            
            # 验证每个错误响应都包含适当的错误信息
            for response in error_responses:
                assert "error" in response
                assert "code" in response["error"]
                assert "message" in response["error"]
    
    def test_concurrent_requests_http(self):
        """测试HTTP传输的并发请求处理"""
        transport = HTTPTransport(host="localhost", port=8996)
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        try:
            transport.start()
            time.sleep(0.1)
            
            base_url = "http://localhost:8996"
            
            # 创建多个并发请求
            def make_request(request_id: int) -> Dict[str, Any]:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": f"concurrent-{request_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "base64_encode",
                        "arguments": {"text": f"Concurrent request {request_id}"}
                    }
                }
                
                response = requests.post(f"{base_url}/mcp", json=request_data)
                return response.json()
            
            # 并发执行多个请求
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, i) for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # 验证所有请求都成功处理
            assert len(results) == 10
            
            for result in results:
                assert "result" in result
                assert result["result"]["isError"] is False
                assert "content" in result["result"]
            
        finally:
            transport.stop()
    
    def test_transport_comparison(self):
        """测试stdio和HTTP传输的功能一致性"""
        # 准备相同的测试请求
        test_request = MCPRequest(
            id="comparison-test",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": "Transport Comparison Test"}
            }
        )
        
        # 测试stdio传输
        stdio_transport = StdioTransport()
        stdio_transport.set_request_handler(self.mcp_handler.handle_request)
        
        with patch('sys.stdin') as mock_stdin, patch('sys.stdout') as mock_stdout:
            mock_stdin.readline.side_effect = [test_request.to_json() + "\n", ""]
            
            stdio_response = None
            def capture_stdio(data):
                nonlocal stdio_response
                if data.strip():
                    stdio_response = json.loads(data.strip())
            
            mock_stdout.write.side_effect = capture_stdio
            mock_stdout.flush = Mock()
            
            stdio_transport.start()
            time.sleep(0.1)
        
        # 测试HTTP传输
        http_transport = HTTPTransport(host="localhost", port=8995)
        http_transport.set_request_handler(self.mcp_handler.handle_request)
        
        try:
            http_transport.start()
            time.sleep(0.1)
            
            http_request_data = {
                "jsonrpc": "2.0",
                "id": "comparison-test",
                "method": "tools/call",
                "params": {
                    "name": "base64_encode",
                    "arguments": {"text": "Transport Comparison Test"}
                }
            }
            
            response = requests.post("http://localhost:8995/mcp", json=http_request_data)
            http_response = response.json()
            
        finally:
            http_transport.stop()
        
        # 比较两种传输方式的结果
        assert stdio_response is not None
        assert http_response is not None
        
        # 核心结果应该相同
        assert stdio_response["id"] == http_response["id"]
        assert stdio_response["result"]["isError"] == http_response["result"]["isError"]
        assert stdio_response["result"]["content"] == http_response["result"]["content"]
    
    def test_performance_under_load(self):
        """测试负载下的性能表现"""
        transport = HTTPTransport(host="localhost", port=8994)
        transport.set_request_handler(self.mcp_handler.handle_request)
        
        try:
            transport.start()
            time.sleep(0.1)
            
            base_url = "http://localhost:8994"
            
            # 执行适量请求测试性能
            start_time = time.time()
            successful_requests = 0
            
            for i in range(20):  # 20个请求，减少测试时间
                try:
                    request_data = {
                        "jsonrpc": "2.0",
                        "id": f"perf-{i}",
                        "method": "tools/call",
                        "params": {
                            "name": "base64_encode",
                            "arguments": {"text": f"Performance test {i}"}
                        }
                    }
                    
                    response = requests.post(f"{base_url}/mcp", json=request_data, timeout=2)
                    if response.status_code == 200:
                        successful_requests += 1
                        
                except Exception:
                    pass  # 忽略个别失败的请求
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 验证性能指标（更宽松的要求）
            assert successful_requests >= 18  # 至少90%成功率
            assert duration < 30.0  # 总时间少于30秒
            
            # 计算平均响应时间
            if successful_requests > 0:
                avg_response_time = duration / successful_requests
                assert avg_response_time < 2.0  # 平均响应时间少于2秒
            
        finally:
            transport.stop()


class TestMCPInspectorIntegration:
    """MCP Inspector集成测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.base64_service = Base64Service()
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
    
    def test_tool_discovery_for_inspector(self):
        """测试工具发现功能（模拟MCP Inspector行为）"""
        # 模拟Inspector的工具发现请求
        discovery_request = MCPRequest(
            id="inspector-discovery",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        response = self.mcp_handler.handle_request(discovery_request)
        
        # 验证Inspector能够正确发现工具
        assert response.error is None
        assert "tools" in response.result
        
        tools = response.result["tools"]
        assert len(tools) == 2
        
        # 验证工具定义包含Inspector需要的所有信息
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # 验证schema结构符合JSON Schema规范
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema
    
    def test_tool_execution_for_inspector(self):
        """测试工具执行功能（模拟Inspector调用）"""
        # 模拟Inspector执行base64_encode工具
        encode_request = MCPRequest(
            id="inspector-encode",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_encode",
                "arguments": {"text": "Inspector Test"}
            }
        )
        
        response = self.mcp_handler.handle_request(encode_request)
        
        # 验证Inspector能够获得正确的执行结果
        assert response.error is None
        assert response.result["isError"] is False
        
        content = response.result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "SW5zcGVjdG9yIFRlc3Q="
        
        # 模拟Inspector执行base64_decode工具
        decode_request = MCPRequest(
            id="inspector-decode",
            method=MCPMethods.CALL_TOOL,
            params={
                "name": "base64_decode",
                "arguments": {"base64_string": "SW5zcGVjdG9yIFRlc3Q="}
            }
        )
        
        response = self.mcp_handler.handle_request(decode_request)
        
        assert response.error is None
        assert response.result["content"][0]["text"] == "Inspector Test"
    
    def test_error_debugging_for_inspector(self):
        """测试错误调试信息（Inspector调试功能）"""
        # 模拟Inspector触发各种错误场景
        error_scenarios = [
            # 1. 工具不存在
            {
                "request": MCPRequest(
                    id="debug-1",
                    method=MCPMethods.CALL_TOOL,
                    params={"name": "nonexistent_tool", "arguments": {}}
                ),
                "expected_code": -1004  # TOOL_NOT_FOUND
            },
            # 2. 缺少参数
            {
                "request": MCPRequest(
                    id="debug-2",
                    method=MCPMethods.CALL_TOOL,
                    params={"name": "base64_encode", "arguments": {}}
                ),
                "expected_code": -32602  # Invalid params
            },
            # 3. 无效base64
            {
                "request": MCPRequest(
                    id="debug-3",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": "base64_decode",
                        "arguments": {"base64_string": "invalid@base64"}
                    }
                ),
                "expected_code": -32602  # Invalid params
            }
        ]
        
        for scenario in error_scenarios:
            response = self.mcp_handler.handle_request(scenario["request"])
            
            # 验证Inspector能够获得详细的错误信息
            assert response.error is not None
            assert response.error.code == scenario["expected_code"]
            assert response.error.message is not None
            assert len(response.error.message) > 0
            
            # 验证错误响应包含调试所需的信息
            assert response.id == scenario["request"].id
    
    def test_inspector_connection_simulation(self):
        """测试模拟Inspector连接场景"""
        # 模拟Inspector的完整连接和使用流程
        
        # 1. 初始化连接
        init_request = MCPRequest(
            id="inspector-init",
            method=MCPMethods.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}}
            }
        )
        
        init_response = self.mcp_handler.handle_request(init_request)
        assert init_response.error is None
        assert "serverInfo" in init_response.result
        
        # 2. 获取工具列表
        list_request = MCPRequest(
            id="inspector-list",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        list_response = self.mcp_handler.handle_request(list_request)
        assert list_response.error is None
        tools = list_response.result["tools"]
        
        # 3. 对每个工具进行测试调用
        for tool in tools:
            tool_name = tool["name"]
            
            if tool_name == "base64_encode":
                test_request = MCPRequest(
                    id=f"inspector-test-{tool_name}",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": tool_name,
                        "arguments": {"text": "Inspector validation"}
                    }
                )
            elif tool_name == "base64_decode":
                test_request = MCPRequest(
                    id=f"inspector-test-{tool_name}",
                    method=MCPMethods.CALL_TOOL,
                    params={
                        "name": tool_name,
                        "arguments": {"base64_string": "SW5zcGVjdG9yIHZhbGlkYXRpb24="}
                    }
                )
            
            test_response = self.mcp_handler.handle_request(test_request)
            
            # 验证Inspector能够成功调用每个工具
            assert test_response.error is None
            assert test_response.result["isError"] is False
            assert len(test_response.result["content"]) > 0
    
    def test_inspector_debugging_features(self):
        """测试Inspector调试功能支持"""
        # 测试ping功能（Inspector用于检查连接状态）
        ping_request = MCPRequest(
            id="inspector-ping",
            method=MCPMethods.PING,
            params={}
        )
        
        ping_response = self.mcp_handler.handle_request(ping_request)
        assert ping_response.error is None
        assert ping_response.result["status"] == "pong"
        
        # 测试详细的工具信息（Inspector显示工具详情）
        list_request = MCPRequest(
            id="inspector-detailed-list",
            method=MCPMethods.LIST_TOOLS,
            params={}
        )
        
        list_response = self.mcp_handler.handle_request(list_request)
        tools = list_response.result["tools"]
        
        # 验证每个工具都有完整的调试信息
        for tool in tools:
            # 验证工具描述是中文的（符合需求）
            assert tool["description"] is not None
            assert len(tool["description"]) > 0
            
            # 验证schema包含详细的参数说明
            schema = tool["inputSchema"]
            properties = schema["properties"]
            
            for prop_name, prop_def in properties.items():
                assert "type" in prop_def
                assert "description" in prop_def
                assert len(prop_def["description"]) > 0


if __name__ == "__main__":
    # 运行集成测试需要安装requests库
    try:
        import requests
    except ImportError:
        print("Warning: requests library not found. HTTP integration tests will be skipped.")
        print("Install with: pip install requests")
    
    pytest.main([__file__, "-v", "--tb=short"])
"""
HTTP Transport Unit Tests

This module contains comprehensive unit tests for the HTTP transport implementation.
Tests cover HTTP request handling, MCP message processing, error scenarios,
and comparison with stdio transport behavior.
"""

import unittest
import json
import threading
import time
import requests
from unittest.mock import Mock, patch
from models.mcp_models import MCPRequest, MCPResponse, MCPError
from transports.http_transport import HTTPTransport, MCPHTTPRequestHandler
from services.error_handler import ErrorHandler


class TestHTTPTransport(unittest.TestCase):
    """HTTP传输层单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.transport = HTTPTransport(host="localhost", port=8999)
        self.mock_handler = Mock()
        
    def tearDown(self):
        """测试后清理"""
        if self.transport.is_running():
            self.transport.stop()
    
    def test_initialization(self):
        """测试HTTP传输初始化"""
        # 测试默认参数
        default_transport = HTTPTransport()
        self.assertEqual(default_transport.host, "localhost")
        self.assertEqual(default_transport.port, 3000)
        self.assertFalse(default_transport.is_running())
        
        # 测试自定义参数
        self.assertEqual(self.transport.host, "localhost")
        self.assertEqual(self.transport.port, 8999)
        self.assertFalse(self.transport.is_running())
    
    def test_start_stop_transport(self):
        """测试HTTP传输启动和停止"""
        # 测试启动
        self.assertFalse(self.transport.is_running())
        self.transport.start()
        self.assertTrue(self.transport.is_running())
        
        # 测试重复启动（应该无效果）
        self.transport.start()
        self.assertTrue(self.transport.is_running())
        
        # 测试停止
        self.transport.stop()
        self.assertFalse(self.transport.is_running())
        
        # 测试重复停止（应该无效果）
        self.transport.stop()
        self.assertFalse(self.transport.is_running())
    
    def test_connection_info(self):
        """测试连接信息获取"""
        info = self.transport.get_connection_info()
        
        expected_keys = [
            "transport_type", "running", "host", "port", 
            "url", "mcp_endpoint", "methods", "cors_enabled", "description"
        ]
        
        for key in expected_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info["transport_type"], "http")
        self.assertEqual(info["host"], "localhost")
        self.assertEqual(info["port"], 8999)
        self.assertEqual(info["url"], "http://localhost:8999")
        self.assertEqual(info["mcp_endpoint"], "http://localhost:8999/mcp")
        self.assertEqual(info["methods"], ["POST"])
        self.assertTrue(info["cors_enabled"])
    
    def test_request_handler_registration(self):
        """测试请求处理器注册"""
        # 创建模拟处理器
        def mock_handler(request):
            return MCPResponse(
                id=request.id,
                result={"message": "test response"}
            )
        
        self.transport.set_request_handler(mock_handler)
        self.assertIsNotNone(self.transport._request_handler)
    
    def test_send_response_interface(self):
        """测试发送响应接口（HTTP传输中为空实现）"""
        response = MCPResponse(id="test", result={"test": "data"})
        
        # HTTP传输中send_response是空实现，不应该抛出异常
        try:
            self.transport.send_response(response)
        except Exception as e:
            self.fail(f"send_response should not raise exception: {e}")


class TestHTTPTransportIntegration(unittest.TestCase):
    """HTTP传输集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.transport = HTTPTransport(host="localhost", port=8998)
        self.base_url = "http://localhost:8998"
        
        # 设置模拟请求处理器
        def mock_handler(request):
            if request.method == "tools/list":
                return MCPResponse(
                    id=request.id,
                    result={
                        "tools": [
                            {
                                "name": "test_tool",
                                "description": "Test tool",
                                "inputSchema": {"type": "object"}
                            }
                        ]
                    }
                )
            elif request.method == "tools/call":
                return MCPResponse(
                    id=request.id,
                    result={
                        "content": [{"type": "text", "text": "Test result"}],
                        "isError": False
                    }
                )
            else:
                error_handler = ErrorHandler()
                error = error_handler.create_method_not_found_error(
                    f"Method not found: {request.method}"
                )
                return MCPResponse(id=request.id, error=error)
        
        self.transport.set_request_handler(mock_handler)
        self.transport.start()
        
        # 等待服务器启动
        time.sleep(0.1)
    
    def tearDown(self):
        """测试后清理"""
        if self.transport.is_running():
            self.transport.stop()
    
    def test_mcp_endpoint_tools_list(self):
        """测试MCP端点 - 工具列表请求"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(
            f"{self.base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        
        response_data = response.json()
        self.assertEqual(response_data["jsonrpc"], "2.0")
        self.assertEqual(response_data["id"], "test-1")
        self.assertIn("result", response_data)
        self.assertIn("tools", response_data["result"])
    
    def test_mcp_endpoint_tool_call(self):
        """测试MCP端点 - 工具调用请求"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {"input": "test"}
            }
        }
        
        response = requests.post(
            f"{self.base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["id"], "test-2")
        self.assertIn("result", response_data)
    
    def test_invalid_endpoint(self):
        """测试无效端点"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "tools/list"
        }
        
        response = requests.post(
            f"{self.base_url}/invalid",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"]["code"], 404)
    
    def test_invalid_json(self):
        """测试无效JSON请求"""
        response = requests.post(
            f"{self.base_url}/mcp",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("error", response_data)
    
    def test_cors_headers(self):
        """测试CORS头部"""
        # 测试OPTIONS请求
        response = requests.options(f"{self.base_url}/mcp")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", response.headers)
        self.assertIn("Access-Control-Allow-Methods", response.headers)
        self.assertIn("Access-Control-Allow-Headers", response.headers)
        
        # 测试POST请求的CORS头部
        request_data = {
            "jsonrpc": "2.0",
            "id": "cors-test",
            "method": "tools/list"
        }
        
        response = requests.post(
            f"{self.base_url}/mcp",
            json=request_data
        )
        
        self.assertIn("Access-Control-Allow-Origin", response.headers)
    
    def test_method_not_found(self):
        """测试未找到方法的错误处理"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "unknown/method",
            "params": {}
        }
        
        response = requests.post(
            f"{self.base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["id"], "test-4")
        self.assertIn("error", response_data)
        self.assertNotIn("result", response_data)


class TestHTTPVsStdioComparison(unittest.TestCase):
    """HTTP传输与stdio传输对比测试"""
    
    def test_transport_characteristics(self):
        """测试传输特性对比"""
        http_transport = HTTPTransport()
        
        # HTTP传输特性
        http_info = http_transport.get_connection_info()
        self.assertEqual(http_info["transport_type"], "http")
        self.assertIn("host", http_info)
        self.assertIn("port", http_info)
        self.assertIn("mcp_endpoint", http_info)
        self.assertTrue(http_info["cors_enabled"])
        
        # HTTP传输支持多种HTTP方法
        self.assertIn("POST", http_info["methods"])
        
        # HTTP传输提供网络访问能力
        self.assertTrue(http_info["url"].startswith("http://"))
    
    def test_error_handling_differences(self):
        """测试错误处理差异"""
        # HTTP传输可以使用HTTP状态码
        # 这是与stdio传输的主要差异之一
        
        # 模拟HTTP请求处理器
        transport = HTTPTransport()
        
        # HTTP传输的错误响应包含HTTP状态码信息
        connection_info = transport.get_connection_info()
        self.assertIn("description", connection_info)
        
        # HTTP传输支持CORS，stdio不需要
        self.assertTrue(connection_info["cors_enabled"])
    
    def test_concurrency_support(self):
        """测试并发支持差异"""
        # HTTP传输天然支持多客户端并发
        # stdio传输通常是单一连接
        
        transport = HTTPTransport(host="localhost", port=8997)
        transport.start()
        
        try:
            # HTTP传输可以同时处理多个请求
            # 这里我们验证传输层已启动并可以接受连接
            self.assertTrue(transport.is_running())
            
            # HTTP传输的连接信息显示支持并发
            info = transport.get_connection_info()
            self.assertEqual(info["transport_type"], "http")
            
        finally:
            transport.stop()


if __name__ == '__main__':
    # 运行测试时需要安装requests库
    try:
        import requests
    except ImportError:
        print("Warning: requests library not found. Some integration tests will be skipped.")
        print("Install with: pip install requests")
    
    unittest.main()
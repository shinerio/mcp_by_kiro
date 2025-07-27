"""
HTTP API Server Unit Tests

This module contains comprehensive unit tests for the HTTP API server implementation.
Tests cover REST API endpoints, request validation, error handling, and CORS support.
"""

import unittest
import json
import threading
import time
import requests
from unittest.mock import Mock, patch
from servers.http_server import HTTPServer, HTTPAPIRequestHandler
from services.base64_service import Base64Service


class TestHTTPServer(unittest.TestCase):
    """HTTP API服务器单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.server = HTTPServer(host="localhost", port=8899)
        
    def tearDown(self):
        """测试后清理"""
        if self.server.is_running():
            self.server.stop()
    
    def test_initialization(self):
        """测试HTTP服务器初始化"""
        # 测试默认参数
        default_server = HTTPServer()
        self.assertEqual(default_server.host, "localhost")
        self.assertEqual(default_server.port, 8080)
        self.assertFalse(default_server.is_running())
        
        # 测试自定义参数
        self.assertEqual(self.server.host, "localhost")
        self.assertEqual(self.server.port, 8899)
        self.assertFalse(self.server.is_running())
        self.assertIsInstance(self.server.base64_service, Base64Service)
    
    def test_start_stop_server(self):
        """测试HTTP服务器启动和停止"""
        # 测试启动
        self.assertFalse(self.server.is_running())
        self.server.start()
        self.assertTrue(self.server.is_running())
        
        # 测试重复启动（应该无效果）
        self.server.start()
        self.assertTrue(self.server.is_running())
        
        # 测试停止
        self.server.stop()
        self.assertFalse(self.server.is_running())
        
        # 测试重复停止（应该无效果）
        self.server.stop()
        self.assertFalse(self.server.is_running())
    
    def test_server_info(self):
        """测试服务器信息获取"""
        info = self.server.get_server_info()
        
        expected_keys = [
            "server_type", "running", "host", "port", "base_url",
            "endpoints", "methods", "cors_enabled", "content_type"
        ]
        
        for key in expected_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info["server_type"], "http_api")
        self.assertEqual(info["host"], "localhost")
        self.assertEqual(info["port"], 8899)
        self.assertEqual(info["base_url"], "http://localhost:8899")
        self.assertTrue(info["cors_enabled"])
        self.assertEqual(info["content_type"], "application/json")
        
        # 检查端点信息
        endpoints = info["endpoints"]
        self.assertIn("encode", endpoints)
        self.assertIn("decode", endpoints)
        self.assertIn("health", endpoints)
        self.assertIn("api_info", endpoints)


class TestHTTPServerIntegration(unittest.TestCase):
    """HTTP API服务器集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.server = HTTPServer(host="localhost", port=8898)
        self.base_url = "http://localhost:8898"
        self.server.start()
        
        # 等待服务器启动
        time.sleep(0.1)
    
    def tearDown(self):
        """测试后清理"""
        if self.server.is_running():
            self.server.stop()
    
    def test_encode_endpoint_success(self):
        """测试编码端点 - 成功场景"""
        request_data = {
            "text": "Hello, World!"
        }
        
        response = requests.post(
            f"{self.base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
        
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertIn("result", response_data)
        
        # 验证编码结果
        expected_result = "SGVsbG8sIFdvcmxkIQ=="
        self.assertEqual(response_data["result"], expected_result)
    
    def test_encode_endpoint_empty_text(self):
        """测试编码端点 - 空文本"""
        request_data = {
            "text": ""
        }
        
        response = requests.post(
            f"{self.base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["result"], "")
    
    def test_encode_endpoint_missing_text(self):
        """测试编码端点 - 缺少text字段"""
        request_data = {}
        
        response = requests.post(
            f"{self.base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
        self.assertIn("Missing 'text' field", response_data["error"]["message"])
    
    def test_encode_endpoint_invalid_text_type(self):
        """测试编码端点 - 无效的text类型"""
        request_data = {
            "text": 123  # 应该是字符串
        }
        
        response = requests.post(
            f"{self.base_url}/encode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("must be a string", response_data["error"]["message"])
    
    def test_decode_endpoint_success(self):
        """测试解码端点 - 成功场景"""
        request_data = {
            "base64_string": "SGVsbG8sIFdvcmxkIQ=="
        }
        
        response = requests.post(
            f"{self.base_url}/decode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["result"], "Hello, World!")
    
    def test_decode_endpoint_empty_base64(self):
        """测试解码端点 - 空base64字符串"""
        request_data = {
            "base64_string": ""
        }
        
        response = requests.post(
            f"{self.base_url}/decode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
    
    def test_decode_endpoint_invalid_base64(self):
        """测试解码端点 - 无效的base64字符串"""
        request_data = {
            "base64_string": "invalid-base64!"
        }
        
        response = requests.post(
            f"{self.base_url}/decode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)
    
    def test_decode_endpoint_missing_base64_string(self):
        """测试解码端点 - 缺少base64_string字段"""
        request_data = {}
        
        response = requests.post(
            f"{self.base_url}/decode",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("Missing 'base64_string' field", response_data["error"]["message"])
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = requests.get(f"{self.base_url}/health")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertEqual(response_data["status"], "healthy")
        self.assertEqual(response_data["service"], "base64-http-api")
        self.assertIn("version", response_data)
        self.assertIn("endpoints", response_data)
    
    def test_api_info_endpoint(self):
        """测试API信息端点"""
        response = requests.get(f"{self.base_url}/api/info")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertEqual(response_data["name"], "Base64 HTTP API")
        self.assertIn("version", response_data)
        self.assertIn("description", response_data)
        self.assertIn("endpoints", response_data)
        self.assertTrue(response_data["cors_enabled"])
    
    def test_cors_headers(self):
        """测试CORS头部"""
        # 测试OPTIONS请求
        response = requests.options(f"{self.base_url}/encode")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", response.headers)
        self.assertIn("Access-Control-Allow-Methods", response.headers)
        self.assertIn("Access-Control-Allow-Headers", response.headers)
        
        # 测试POST请求的CORS头部
        request_data = {"text": "test"}
        response = requests.post(f"{self.base_url}/encode", json=request_data)
        
        self.assertIn("Access-Control-Allow-Origin", response.headers)
    
    def test_invalid_endpoint(self):
        """测试无效端点"""
        response = requests.post(f"{self.base_url}/invalid")
        
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("Unknown endpoint", response_data["error"]["message"])
    
    def test_invalid_json(self):
        """测试无效JSON请求"""
        response = requests.post(
            f"{self.base_url}/encode",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("Invalid JSON", response_data["error"]["type"])
    
    def test_get_invalid_endpoint(self):
        """测试GET请求无效端点"""
        response = requests.get(f"{self.base_url}/invalid")
        
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        # 现在静态文件服务会处理所有GET请求，所以错误消息会是"File not found"
        self.assertIn("File not found", response_data["error"]["message"])


class TestHTTPServerEdgeCases(unittest.TestCase):
    """HTTP API服务器边界情况测试"""
    
    def setUp(self):
        """测试前准备"""
        self.server = HTTPServer(host="localhost", port=8897)
        self.base_url = "http://localhost:8897"
        self.server.start()
        time.sleep(0.1)
    
    def tearDown(self):
        """测试后清理"""
        if self.server.is_running():
            self.server.stop()
    
    def test_large_text_encoding(self):
        """测试大文本编码"""
        # 创建一个较大的文本（但在限制范围内）
        large_text = "A" * 1000
        
        request_data = {"text": large_text}
        response = requests.post(f"{self.base_url}/encode", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        
        # 验证可以正确解码
        decode_request = {"base64_string": response_data["result"]}
        decode_response = requests.post(f"{self.base_url}/decode", json=decode_request)
        
        self.assertEqual(decode_response.status_code, 200)
        decode_data = decode_response.json()
        self.assertEqual(decode_data["result"], large_text)
    
    def test_unicode_text_handling(self):
        """测试Unicode文本处理"""
        unicode_text = "你好，世界！🌍"
        
        request_data = {"text": unicode_text}
        response = requests.post(f"{self.base_url}/encode", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        
        # 验证可以正确解码
        decode_request = {"base64_string": response_data["result"]}
        decode_response = requests.post(f"{self.base_url}/decode", json=decode_request)
        
        self.assertEqual(decode_response.status_code, 200)
        decode_data = decode_response.json()
        self.assertEqual(decode_data["result"], unicode_text)
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import concurrent.futures
        
        def make_encode_request(text):
            request_data = {"text": f"test-{text}"}
            response = requests.post(f"{self.base_url}/encode", json=request_data)
            return response.status_code == 200
        
        # 并发发送多个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_encode_request, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 所有请求都应该成功
        self.assertTrue(all(results))
    
    def test_empty_request_body(self):
        """测试空请求体"""
        response = requests.post(
            f"{self.base_url}/encode",
            data="",
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])


class TestHTTPServerStaticFiles(unittest.TestCase):
    """HTTP API服务器静态文件服务测试"""
    
    def setUp(self):
        """测试前准备"""
        self.server = HTTPServer(host="localhost", port=8896)
        self.base_url = "http://localhost:8896"
        self.server.start()
        time.sleep(0.1)
    
    def tearDown(self):
        """测试后清理"""
        if self.server.is_running():
            self.server.stop()
    
    def test_serve_index_html(self):
        """测试提供index.html"""
        response = requests.get(f"{self.base_url}/")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("Content-Type", ""))
        # 检查HTML内容而不是具体的中文字符
        self.assertIn("<title>", response.text)
        self.assertIn("Base64", response.text)
        self.assertIn("<!DOCTYPE html>", response.text)
        
        # 测试CORS头部
        self.assertIn("Access-Control-Allow-Origin", response.headers)
    
    def test_serve_css_file(self):
        """测试提供CSS文件"""
        response = requests.get(f"{self.base_url}/styles.css")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("Content-Type", ""))
        # 检查CSS内容而不是具体的中文字符
        self.assertIn("Base64", response.text)
        self.assertIn("body {", response.text)
        self.assertIn("margin: 0;", response.text)
    
    def test_serve_js_file(self):
        """测试提供JavaScript文件"""
        response = requests.get(f"{self.base_url}/app.js")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers.get("Content-Type", "").lower())
        self.assertIn("Base64WebClient", response.text)
    
    def test_file_not_found(self):
        """测试文件不存在的情况"""
        response = requests.get(f"{self.base_url}/nonexistent.html")
        
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("File not found", response_data["error"]["message"])
    
    def test_directory_traversal_protection(self):
        """测试目录遍历攻击防护"""
        # 测试多种目录遍历攻击模式
        test_paths = [
            "/../config.yaml",
            "../config.yaml", 
            "..%2Fconfig.yaml",
            "static/../config.yaml"
        ]
        
        for test_path in test_paths:
            with self.subTest(path=test_path):
                try:
                    response = requests.get(f"{self.base_url}/{test_path}")
                    
                    # 应该返回403或404，但不应该返回200
                    self.assertIn(response.status_code, [403, 404])
                    
                    if response.status_code == 403:
                        response_data = response.json()
                        self.assertFalse(response_data["success"])
                        self.assertIn("Access denied", response_data["error"]["message"])
                except requests.exceptions.InvalidURL:
                    # 如果URL无效，这也是一种保护机制
                    pass
    
    def test_cache_headers(self):
        """测试缓存头部"""
        # 测试HTML文件（无缓存）
        response = requests.get(f"{self.base_url}/")
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))
        
        # 如果有图片文件，可以测试缓存头部
        # 这里我们测试CSS文件（也应该是no-cache）
        response = requests.get(f"{self.base_url}/styles.css")
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))


class TestHTTPServerVsMCPComparison(unittest.TestCase):
    """HTTP API服务器与MCP传输对比测试"""
    
    def test_server_characteristics(self):
        """测试服务器特性对比"""
        server = HTTPServer()
        
        # HTTP API服务器特性
        info = server.get_server_info()
        self.assertEqual(info["server_type"], "http_api")
        self.assertIn("base_url", info)
        self.assertIn("endpoints", info)
        self.assertTrue(info["cors_enabled"])
        
        # HTTP API支持多种HTTP方法
        self.assertIn("GET", info["methods"])
        self.assertIn("POST", info["methods"])
        self.assertIn("OPTIONS", info["methods"])
        
        # HTTP API提供RESTful接口
        endpoints = info["endpoints"]
        self.assertIn("encode", endpoints)
        self.assertIn("decode", endpoints)
        self.assertIn("health", endpoints)
        self.assertIn("web_interface", endpoints)
        self.assertIn("static_files", endpoints)
    
    def test_error_handling_differences(self):
        """测试错误处理差异"""
        # HTTP API使用标准HTTP状态码
        # 这是与MCP传输的主要差异之一
        
        server = HTTPServer()
        info = server.get_server_info()
        
        # HTTP API的错误响应包含HTTP状态码信息
        self.assertEqual(info["content_type"], "application/json")
        
        # HTTP API支持CORS，MCP传输不需要
        self.assertTrue(info["cors_enabled"])
    
    def test_protocol_differences(self):
        """测试协议差异"""
        # HTTP API使用REST风格的端点
        # MCP使用JSON-RPC协议
        
        server = HTTPServer()
        info = server.get_server_info()
        
        # HTTP API有专门的端点
        endpoints = info["endpoints"]
        self.assertTrue(endpoints["encode"].endswith("/encode"))
        self.assertTrue(endpoints["decode"].endswith("/decode"))
        
        # HTTP API支持健康检查
        self.assertIn("health", endpoints)
        
        # HTTP API支持静态文件服务
        self.assertIn("web_interface", endpoints)
        self.assertIn("static_files", endpoints)


if __name__ == '__main__':
    # 运行测试时需要安装requests库
    try:
        import requests
    except ImportError:
        print("Warning: requests library not found. Some integration tests will be skipped.")
        print("Install with: pip install requests")
    
    unittest.main()
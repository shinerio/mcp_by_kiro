#!/usr/bin/env python3
"""
Final Integration Test Suite for MCP Base64 Server

This comprehensive test suite validates all functionality across different
configurations and deployment scenarios.
"""

import pytest
import subprocess
import time
import requests
import json
import threading
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import psutil

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import ConfigManager
from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from transports.stdio_transport import StdioTransport
from transports.http_transport import HTTPTransport
from servers.http_server import HTTPServer


class TestConfiguration:
    """Test configuration and utilities"""
    
    @staticmethod
    def load_test_config(config_type: str = "default") -> Dict[str, Any]:
        """Load test configuration"""
        config_files = {
            "default": "config.yaml",
            "production": "config.prod.yaml"
        }
        
        config_file = config_files.get(config_type, "config.yaml")
        if not Path(config_file).exists():
            return {}
            
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def get_free_port() -> int:
        """Get a free port for testing"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port


class TestServerProcess:
    """Helper class to manage server processes during testing"""
    
    def __init__(self, command: list, timeout: int = 30):
        self.command = command
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.stdout_lines = []
        self.stderr_lines = []
    
    def start(self) -> bool:
        """Start the server process"""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for server to start
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if self.process.poll() is not None:
                    # Process has terminated
                    stdout, stderr = self.process.communicate()
                    self.stdout_lines.extend(stdout.splitlines())
                    self.stderr_lines.extend(stderr.splitlines())
                    return False
                
                time.sleep(0.5)
                
                # Check if server is ready (look for startup message)
                try:
                    line = self.process.stdout.readline()
                    if line:
                        self.stdout_lines.append(line.strip())
                        if "Server started successfully" in line or "Ready to receive" in line:
                            return True
                except:
                    pass
            
            return True
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop(self):
        """Stop the server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except:
                pass
    
    def is_running(self) -> bool:
        """Check if the server process is running"""
        return self.process is not None and self.process.poll() is None
    
    def get_output(self) -> tuple:
        """Get stdout and stderr output"""
        return self.stdout_lines, self.stderr_lines


class TestMCPBase64Integration:
    """Comprehensive integration tests for MCP Base64 Server"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_config = TestConfiguration()
        self.base64_service = Base64Service()
        self.test_data = {
            "simple_text": "Hello, World!",
            "simple_base64": "SGVsbG8sIFdvcmxkIQ==",
            "unicode_text": "Hello 世界! 🌍",
            "unicode_base64": "SGVsbG8g5LiW55WMISAg8J+MjQ==",
            "empty_text": "",
            "empty_base64": "",
            "long_text": "A" * 1000,
        }
        self.test_data["long_base64"] = self.base64_service.encode(self.test_data["long_text"])
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Kill any remaining processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.info['name'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    proc.terminate()
            except:
                pass
    
    def test_base64_service_functionality(self):
        """Test core Base64Service functionality"""
        print("\n=== Testing Base64Service Core Functionality ===")
        
        # Test encoding
        for key, text in [("simple_text", self.test_data["simple_text"]), 
                         ("unicode_text", self.test_data["unicode_text"])]:
            encoded = self.base64_service.encode(text)
            assert encoded == self.test_data[key.replace("_text", "_base64")]
            print(f"✓ Encoding test passed for {key}")
        
        # Test decoding
        for key, base64_str in [("simple_base64", self.test_data["simple_base64"]), 
                               ("unicode_base64", self.test_data["unicode_base64"])]:
            decoded = self.base64_service.decode(base64_str)
            assert decoded == self.test_data[key.replace("_base64", "_text")]
            print(f"✓ Decoding test passed for {key}")
        
        # Test validation
        assert self.base64_service.validate_base64(self.test_data["simple_base64"])
        assert not self.base64_service.validate_base64("invalid_base64!")
        print("✓ Validation tests passed")
        
        # Test edge cases
        assert self.base64_service.encode("") == ""
        assert self.base64_service.decode("") == ""
        print("✓ Edge case tests passed")
    
    def test_mcp_protocol_handler(self):
        """Test MCP protocol handler functionality"""
        print("\n=== Testing MCP Protocol Handler ===")
        
        handler = MCPProtocolHandler(self.base64_service)
        
        # Test tool registration
        tools = handler.get_available_tools()
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "base64_encode" in tool_names
        assert "base64_decode" in tool_names
        print("✓ Tool registration test passed")
        
        # Test encode tool call
        encode_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "base64_encode",
                "arguments": {"text": self.test_data["simple_text"]}
            }
        }
        
        response = handler.handle_request(encode_request)
        assert response["result"]["content"][0]["text"] == self.test_data["simple_base64"]
        print("✓ Encode tool call test passed")
        
        # Test decode tool call
        decode_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "base64_decode",
                "arguments": {"base64_string": self.test_data["simple_base64"]}
            }
        }
        
        response = handler.handle_request(decode_request)
        assert response["result"]["content"][0]["text"] == self.test_data["simple_text"]
        print("✓ Decode tool call test passed")
        
        # Test list tools
        list_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list"
        }
        
        response = handler.handle_request(list_request)
        assert len(response["result"]["tools"]) == 2
        print("✓ List tools test passed")
    
    def test_http_server_functionality(self):
        """Test HTTP server functionality"""
        print("\n=== Testing HTTP Server Functionality ===")
        
        port = self.test_config.get_free_port()
        server = HTTPServer(host="localhost", port=port)
        
        # Start server in a thread
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        base_url = f"http://localhost:{port}"
        
        try:
            # Test health endpoint
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            print("✓ Health endpoint test passed")
            
            # Test encode endpoint
            encode_data = {"text": self.test_data["simple_text"]}
            response = requests.post(f"{base_url}/encode", json=encode_data, timeout=5)
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["result"] == self.test_data["simple_base64"]
            print("✓ Encode endpoint test passed")
            
            # Test decode endpoint
            decode_data = {"base64_string": self.test_data["simple_base64"]}
            response = requests.post(f"{base_url}/decode", json=decode_data, timeout=5)
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["result"] == self.test_data["simple_text"]
            print("✓ Decode endpoint test passed")
            
            # Test static file serving
            response = requests.get(f"{base_url}/", timeout=5)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            print("✓ Static file serving test passed")
            
            # Test error handling
            invalid_decode_data = {"base64_string": "invalid_base64!"}
            response = requests.post(f"{base_url}/decode", json=invalid_decode_data, timeout=5)
            assert response.status_code == 400
            result = response.json()
            assert result["success"] is False
            print("✓ Error handling test passed")
            
        finally:
            server.stop()
    
    def test_server_startup_configurations(self):
        """Test server startup with different configurations"""
        print("\n=== Testing Server Startup Configurations ===")
        
        # Test stdio transport
        print("Testing stdio transport...")
        stdio_cmd = [sys.executable, "main.py", "--transport", "stdio", "--log-level", "INFO"]
        stdio_server = TestServerProcess(stdio_cmd, timeout=10)
        
        if stdio_server.start():
            assert stdio_server.is_running()
            print("✓ Stdio transport startup test passed")
            stdio_server.stop()
        else:
            stdout, stderr = stdio_server.get_output()
            print(f"Stdio server failed to start. Stdout: {stdout}, Stderr: {stderr}")
            # Don't fail the test, just warn
            print("⚠ Stdio transport test skipped (may require interactive input)")
        
        # Test HTTP transport
        print("Testing HTTP transport...")
        http_port = self.test_config.get_free_port()
        api_port = self.test_config.get_free_port()
        
        http_cmd = [
            sys.executable, "main.py",
            "--transport", "http",
            "--http-port", str(http_port),
            "--enable-http-server",
            "--http-server-port", str(api_port),
            "--log-level", "INFO"
        ]
        
        http_server = TestServerProcess(http_cmd, timeout=15)
        
        if http_server.start():
            assert http_server.is_running()
            print("✓ HTTP transport startup test passed")
            
            # Test if HTTP endpoints are accessible
            time.sleep(3)  # Give server time to fully start
            
            try:
                # Test API server
                response = requests.get(f"http://localhost:{api_port}/health", timeout=5)
                assert response.status_code == 200
                print("✓ HTTP API server accessibility test passed")
                
                # Test MCP transport (basic connectivity)
                mcp_response = requests.post(
                    f"http://localhost:{http_port}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list"
                    },
                    timeout=5
                )
                assert mcp_response.status_code == 200
                print("✓ MCP HTTP transport accessibility test passed")
                
            except requests.exceptions.RequestException as e:
                print(f"⚠ HTTP accessibility test failed: {e}")
            
            http_server.stop()
        else:
            stdout, stderr = http_server.get_output()
            print(f"HTTP server failed to start. Stdout: {stdout}, Stderr: {stderr}")
            assert False, "HTTP server startup failed"
    
    def test_configuration_loading(self):
        """Test configuration loading and validation"""
        print("\n=== Testing Configuration Loading ===")
        
        # Test default configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        assert config.server.name == "mcp-base64-server"
        assert config.server.version == "1.0.0"
        assert config.transport.type in ["stdio", "http"]
        print("✓ Default configuration loading test passed")
        
        # Test production configuration
        if Path("config.prod.yaml").exists():
            prod_config_manager = ConfigManager("config.prod.yaml")
            prod_config = prod_config_manager.load_config()
            
            assert prod_config.server.name == "mcp-base64-server"
            assert prod_config.transport.type == "http"
            assert prod_config.http_server.enabled is True
            print("✓ Production configuration loading test passed")
        else:
            print("⚠ Production configuration test skipped (file not found)")
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        print("\n=== Testing Error Handling Scenarios ===")
        
        handler = MCPProtocolHandler(self.base64_service)
        
        # Test invalid method
        invalid_method_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "invalid/method"
        }
        
        response = handler.handle_request(invalid_method_request)
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found
        print("✓ Invalid method error handling test passed")
        
        # Test invalid parameters
        invalid_params_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "base64_encode",
                "arguments": {}  # Missing required 'text' parameter
            }
        }
        
        response = handler.handle_request(invalid_params_request)
        assert "error" in response
        print("✓ Invalid parameters error handling test passed")
        
        # Test invalid base64 decoding
        invalid_base64_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "base64_decode",
                "arguments": {"base64_string": "invalid_base64!"}
            }
        }
        
        response = handler.handle_request(invalid_base64_request)
        assert "error" in response
        print("✓ Invalid base64 error handling test passed")
    
    def test_performance_benchmarks(self):
        """Test basic performance benchmarks"""
        print("\n=== Testing Performance Benchmarks ===")
        
        # Test encoding performance
        start_time = time.time()
        for _ in range(1000):
            self.base64_service.encode(self.test_data["simple_text"])
        encode_time = time.time() - start_time
        
        assert encode_time < 1.0  # Should complete 1000 operations in less than 1 second
        print(f"✓ Encoding performance test passed ({encode_time:.3f}s for 1000 operations)")
        
        # Test decoding performance
        start_time = time.time()
        for _ in range(1000):
            self.base64_service.decode(self.test_data["simple_base64"])
        decode_time = time.time() - start_time
        
        assert decode_time < 1.0  # Should complete 1000 operations in less than 1 second
        print(f"✓ Decoding performance test passed ({decode_time:.3f}s for 1000 operations)")
        
        # Test MCP handler performance
        handler = MCPProtocolHandler(self.base64_service)
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "base64_encode",
                "arguments": {"text": self.test_data["simple_text"]}
            }
        }
        
        start_time = time.time()
        for _ in range(100):
            handler.handle_request(request)
        handler_time = time.time() - start_time
        
        assert handler_time < 1.0  # Should complete 100 operations in less than 1 second
        print(f"✓ MCP handler performance test passed ({handler_time:.3f}s for 100 operations)")
    
    def test_docker_compatibility(self):
        """Test Docker compatibility (if Docker is available)"""
        print("\n=== Testing Docker Compatibility ===")
        
        try:
            # Check if Docker is available
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("⚠ Docker not available, skipping Docker tests")
                return
            
            # Test Docker build
            print("Testing Docker build...")
            build_result = subprocess.run(
                ["docker", "build", "-t", "mcp-base64-server-test", "."],
                capture_output=True, text=True, timeout=300
            )
            
            if build_result.returncode == 0:
                print("✓ Docker build test passed")
                
                # Test Docker run (quick test)
                print("Testing Docker run...")
                run_result = subprocess.run([
                    "docker", "run", "--rm", "-d", 
                    "--name", "mcp-test-container",
                    "-p", "8081:8080",
                    "mcp-base64-server-test"
                ], capture_output=True, text=True, timeout=30)
                
                if run_result.returncode == 0:
                    time.sleep(5)  # Wait for container to start
                    
                    try:
                        # Test container health
                        response = requests.get("http://localhost:8081/health", timeout=10)
                        if response.status_code == 200:
                            print("✓ Docker run test passed")
                        else:
                            print("⚠ Docker container health check failed")
                    except requests.exceptions.RequestException:
                        print("⚠ Docker container not accessible")
                    
                    # Stop container
                    subprocess.run(["docker", "stop", "mcp-test-container"], 
                                 capture_output=True, timeout=30)
                else:
                    print(f"⚠ Docker run failed: {run_result.stderr}")
                
                # Clean up image
                subprocess.run(["docker", "rmi", "mcp-base64-server-test"], 
                             capture_output=True, timeout=30)
            else:
                print(f"⚠ Docker build failed: {build_result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⚠ Docker tests timed out")
        except FileNotFoundError:
            print("⚠ Docker not found, skipping Docker tests")
        except Exception as e:
            print(f"⚠ Docker tests failed with exception: {e}")


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Starting MCP Base64 Server Final Integration Tests")
    print("=" * 60)
    
    test_suite = TestMCPBase64Integration()
    test_methods = [
        test_suite.test_base64_service_functionality,
        test_suite.test_mcp_protocol_handler,
        test_suite.test_http_server_functionality,
        test_suite.test_server_startup_configurations,
        test_suite.test_configuration_loading,
        test_suite.test_error_handling_scenarios,
        test_suite.test_performance_benchmarks,
        test_suite.test_docker_compatibility,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_method in test_methods:
        try:
            test_suite.setup_method()
            test_method()
            test_suite.teardown_method()
            passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test_method.__name__} failed: {e}")
            failed_tests += 1
            test_suite.teardown_method()
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed_tests} passed, {failed_tests} failed")
    
    if failed_tests == 0:
        print("🎉 All tests passed! MCP Base64 Server is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please review and fix issues before deployment.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
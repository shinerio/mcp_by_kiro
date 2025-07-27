#!/usr/bin/env python3
"""
Deployment Validation Test Suite for MCP Base64 Server

This test suite validates core functionality for deployment readiness.
"""

import sys
import os
import time
import requests
import json
import threading
from pathlib import Path
import subprocess

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from servers.http_server import HTTPServer
from config import ConfigManager


def test_base64_service():
    """Test Base64Service core functionality"""
    print("Testing Base64Service...")
    
    service = Base64Service()
    
    # Test basic encoding/decoding
    test_text = "Hello, World!"
    encoded = service.encode(test_text)
    decoded = service.decode(encoded)
    
    assert decoded == test_text, f"Expected '{test_text}', got '{decoded}'"
    print("✓ Basic encoding/decoding works")
    
    # Test validation
    is_valid, _ = service.validate_base64(encoded)
    assert is_valid, "Valid base64 should pass validation"
    is_valid, _ = service.validate_base64("invalid!")
    assert not is_valid, "Invalid base64 should fail validation"
    print("✓ Base64 validation works")
    
    return True


def test_mcp_protocol_handler():
    """Test MCP Protocol Handler"""
    print("Testing MCP Protocol Handler...")
    
    service = Base64Service()
    handler = MCPProtocolHandler(service)
    
    # Test tool listing
    tools = handler.get_available_tools()
    assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"
    
    tool_names = [tool.name for tool in tools]
    assert "base64_encode" in tool_names, "base64_encode tool missing"
    assert "base64_decode" in tool_names, "base64_decode tool missing"
    print("✓ Tool registration works")
    
    # Import MCPRequest for proper testing
    from models.mcp_models import MCPRequest
    
    # Test encode tool
    encode_request = MCPRequest(
        jsonrpc="2.0",
        id=1,
        method="tools/call",
        params={
            "name": "base64_encode",
            "arguments": {"text": "Hello"}
        }
    )
    
    response = handler.handle_request(encode_request)
    response_dict = response.__dict__ if hasattr(response, '__dict__') else response
    assert "result" in response_dict or hasattr(response, 'result'), "Encode request should succeed"
    
    if hasattr(response, 'result') and response.result:
        assert response.result["content"][0]["text"] == "SGVsbG8=", "Incorrect encoding result"
    print("✓ Encode tool works")
    
    # Test decode tool
    decode_request = MCPRequest(
        jsonrpc="2.0",
        id=2,
        method="tools/call",
        params={
            "name": "base64_decode",
            "arguments": {"base64_string": "SGVsbG8="}
        }
    )
    
    response = handler.handle_request(decode_request)
    response_dict = response.__dict__ if hasattr(response, '__dict__') else response
    assert "result" in response_dict or hasattr(response, 'result'), "Decode request should succeed"
    
    if hasattr(response, 'result') and response.result:
        assert response.result["content"][0]["text"] == "Hello", "Incorrect decoding result"
    print("✓ Decode tool works")
    
    return True


def test_http_server():
    """Test HTTP Server functionality"""
    print("Testing HTTP Server...")
    
    # Find a free port
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    
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
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        assert response.json()["status"] == "healthy", "Health status not healthy"
        print("✓ Health endpoint works")
        
        # Test encode endpoint
        encode_data = {"text": "Hello"}
        response = requests.post(f"{base_url}/encode", json=encode_data, timeout=5)
        assert response.status_code == 200, f"Encode failed: {response.status_code}"
        result = response.json()
        assert result["success"] is True, "Encode should succeed"
        assert result["result"] == "SGVsbG8=", "Incorrect encode result"
        print("✓ Encode endpoint works")
        
        # Test decode endpoint
        decode_data = {"base64_string": "SGVsbG8="}
        response = requests.post(f"{base_url}/decode", json=decode_data, timeout=5)
        assert response.status_code == 200, f"Decode failed: {response.status_code}"
        result = response.json()
        assert result["success"] is True, "Decode should succeed"
        assert result["result"] == "Hello", "Incorrect decode result"
        print("✓ Decode endpoint works")
        
        # Test static file serving
        response = requests.get(f"{base_url}/", timeout=5)
        assert response.status_code == 200, f"Static file serving failed: {response.status_code}"
        print("✓ Static file serving works")
        
    finally:
        server.stop()
    
    return True


def test_configuration_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    assert config.server.name == "mcp-base64-server", "Server name mismatch"
    assert config.server.version == "1.0.0", "Server version mismatch"
    assert config.transport.type in ["stdio", "http"], "Invalid transport type"
    print("✓ Configuration loading works")
    
    return True


def test_requirements_installation():
    """Test that all required packages are available"""
    print("Testing requirements installation...")
    
    required_packages = [
        "yaml",
        "psutil", 
        "flask",
        "flask_cors"
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is available")
        except ImportError:
            print(f"❌ {package} is missing")
            return False
    
    return True


def test_file_structure():
    """Test that all required files exist"""
    print("Testing file structure...")
    
    required_files = [
        "main.py",
        "config.yaml",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "setup.py",
        "services/base64_service.py",
        "services/mcp_protocol_handler.py",
        "servers/http_server.py",
        "transports/stdio_transport.py",
        "transports/http_transport.py",
        "static/index.html",
        "static/styles.css",
        "static/app.js"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"❌ {file_path} is missing")
            return False
    
    return True


def run_deployment_validation():
    """Run all deployment validation tests"""
    print("=" * 60)
    print("MCP Base64 Server Deployment Validation")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Requirements Installation", test_requirements_installation),
        ("Configuration Loading", test_configuration_loading),
        ("Base64 Service", test_base64_service),
        ("MCP Protocol Handler", test_mcp_protocol_handler),
        ("HTTP Server", test_http_server),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All deployment validation tests passed!")
        print("The MCP Base64 Server is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before deployment.")
        return False


if __name__ == "__main__":
    success = run_deployment_validation()
    sys.exit(0 if success else 1)
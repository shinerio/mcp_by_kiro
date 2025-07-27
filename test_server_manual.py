#!/usr/bin/env python3
"""
Manual test script for MCP Base64 Server

This script tests both the MCP transport and HTTP API server functionality.
"""

import requests
import json
import time
import sys
from typing import Dict, Any


def test_http_api_server(base_url: str = "http://localhost:8080") -> None:
    """
    Test the HTTP API server endpoints
    
    Args:
        base_url: Base URL of the HTTP API server
    """
    print("🧪 Testing HTTP API Server")
    print("=" * 50)
    
    # Test health endpoint
    try:
        print("Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test encode endpoint
    try:
        print("\nTesting encode endpoint...")
        test_text = "Hello, MCP Base64 Server!"
        payload = {"text": test_text}
        
        response = requests.post(
            f"{base_url}/encode",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                encoded = result.get("result")
                print(f"✅ Encode successful")
                print(f"   Input: {test_text}")
                print(f"   Output: {encoded}")
                
                # Test decode with the encoded result
                print("\nTesting decode endpoint...")
                decode_payload = {"base64_string": encoded}
                
                decode_response = requests.post(
                    f"{base_url}/decode",
                    json=decode_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if decode_response.status_code == 200:
                    decode_result = decode_response.json()
                    if decode_result.get("success"):
                        decoded = decode_result.get("result")
                        print(f"✅ Decode successful")
                        print(f"   Input: {encoded}")
                        print(f"   Output: {decoded}")
                        
                        if decoded == test_text:
                            print("✅ Round-trip test passed!")
                        else:
                            print("❌ Round-trip test failed!")
                    else:
                        print(f"❌ Decode failed: {decode_result}")
                else:
                    print(f"❌ Decode request failed: {decode_response.status_code}")
            else:
                print(f"❌ Encode failed: {result}")
        else:
            print(f"❌ Encode request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Encode/decode test error: {e}")
    
    # Test API info endpoint
    try:
        print("\nTesting API info endpoint...")
        response = requests.get(f"{base_url}/api/info", timeout=5)
        if response.status_code == 200:
            print("✅ API info retrieved successfully")
            api_info = response.json()
            print(f"   API Name: {api_info.get('name')}")
            print(f"   Version: {api_info.get('version')}")
            print(f"   Endpoints: {len(api_info.get('endpoints', {}))}")
        else:
            print(f"❌ API info failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API info error: {e}")


def test_mcp_transport(base_url: str = "http://localhost:3000") -> None:
    """
    Test the MCP HTTP transport
    
    Args:
        base_url: Base URL of the MCP transport
    """
    print("\n🧪 Testing MCP HTTP Transport")
    print("=" * 50)
    
    mcp_url = f"{base_url}/mcp"
    
    # Test list_tools
    try:
        print("Testing list_tools...")
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(
            mcp_url,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                tools = result["result"].get("tools", [])
                print(f"✅ List tools successful")
                print(f"   Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool.get('name')}: {tool.get('description')}")
            else:
                print(f"❌ List tools failed: {result}")
        else:
            print(f"❌ List tools request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ List tools error: {e}")
    
    # Test base64_encode tool
    try:
        print("\nTesting base64_encode tool...")
        test_text = "Hello from MCP!"
        request_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "base64_encode",
                "arguments": {
                    "text": test_text
                }
            }
        }
        
        response = requests.post(
            mcp_url,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                content = result["result"].get("content")
                print(f"✅ Base64 encode successful")
                print(f"   Input: {test_text}")
                print(f"   Output: {content}")
                
                # Test base64_decode tool
                print("\nTesting base64_decode tool...")
                decode_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "base64_decode",
                        "arguments": {
                            "base64_string": content
                        }
                    }
                }
                
                decode_response = requests.post(
                    mcp_url,
                    json=decode_request,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if decode_response.status_code == 200:
                    decode_result = decode_response.json()
                    if "result" in decode_result:
                        decoded_content = decode_result["result"].get("content")
                        print(f"✅ Base64 decode successful")
                        print(f"   Input: {content}")
                        print(f"   Output: {decoded_content}")
                        
                        if decoded_content == test_text:
                            print("✅ MCP round-trip test passed!")
                        else:
                            print("❌ MCP round-trip test failed!")
                    else:
                        print(f"❌ Base64 decode failed: {decode_result}")
                else:
                    print(f"❌ Base64 decode request failed: {decode_response.status_code}")
            else:
                print(f"❌ Base64 encode failed: {result}")
        else:
            print(f"❌ Base64 encode request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ MCP tool test error: {e}")


def main():
    """Main test function"""
    print("🚀 MCP Base64 Server Manual Test")
    print("=" * 60)
    
    # Wait a moment for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Test HTTP API server
    test_http_api_server()
    
    # Test MCP transport
    test_mcp_transport()
    
    print("\n" + "=" * 60)
    print("✅ Manual testing completed!")
    print("Check the results above for any failures.")


if __name__ == "__main__":
    main()
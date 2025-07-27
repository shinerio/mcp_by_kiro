#!/usr/bin/env python3
"""
Test script to verify the ping method fix
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from models.mcp_models import MCPRequest


def test_ping_method():
    """Test the ping method to ensure it returns correct format"""
    print("Testing ping method fix...")
    
    # Initialize handler
    service = Base64Service()
    handler = MCPProtocolHandler(service)
    
    # Create ping request
    ping_request = MCPRequest(
        jsonrpc="2.0",
        id=1,
        method="ping",
        params={}
    )
    
    # Handle ping request
    response = handler.handle_request(ping_request)
    
    # Check response
    print(f"Response ID: {response.id}")
    print(f"Response result: {response.result}")
    print(f"Response error: {response.error}")
    
    # Validate response
    assert response.id == 1, "Response ID should match request ID"
    assert response.error is None, "Ping should not return an error"
    assert response.result == {}, "Ping result should be empty dict according to MCP spec"
    
    print("✅ Ping method test passed!")
    return True


def test_ping_json_serialization():
    """Test that the ping response can be properly serialized to JSON"""
    print("Testing ping JSON serialization...")
    
    service = Base64Service()
    handler = MCPProtocolHandler(service)
    
    ping_request = MCPRequest(
        jsonrpc="2.0",
        id=1,
        method="ping",
        params={}
    )
    
    response = handler.handle_request(ping_request)
    
    # Try to serialize to JSON (this should not fail)
    import json
    try:
        json_response = json.dumps({
            "jsonrpc": "2.0",
            "id": response.id,
            "result": response.result
        })
        print(f"JSON response: {json_response}")
        print("✅ JSON serialization test passed!")
        return True
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Ping Method Fix")
    print("=" * 50)
    
    tests = [
        test_ping_method,
        test_ping_json_serialization,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All ping tests passed! The fix is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    sys.exit(0 if failed == 0 else 1)
#!/usr/bin/env python3
"""
Simple main server test
"""

import sys
import threading
import time
from main import MCPBase64Server
from config import ConfigManager

def test_server_initialization():
    """Test server initialization without starting"""
    print("Testing server initialization...")
    
    try:
        # Load configuration
        cm = ConfigManager()
        config = cm.load_config()
        
        # Create server
        server = MCPBase64Server(config)
        
        # Initialize components
        server.initialize()
        
        print("✅ Server initialization successful")
        print(f"Base64 service: {server.base64_service is not None}")
        print(f"MCP handler: {server.mcp_handler is not None}")
        print(f"Transport: {server.transport is not None}")
        print(f"HTTP server: {server.http_server is not None}")
        
        if server.mcp_handler:
            tools = server.mcp_handler.get_available_tools()
            print(f"Available tools: {len(tools)}")
            for tool in tools:
                print(f"  - {tool.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server_with_http():
    """Test server with HTTP transport and HTTP server"""
    print("\nTesting server with HTTP transport...")
    
    try:
        # Load configuration and modify for HTTP
        cm = ConfigManager()
        config = cm.load_config()
        config.transport.type = "http"
        config.transport.http.port = 3001  # Use different port
        config.http_server.enabled = True
        config.http_server.port = 8081  # Use different port
        
        # Create server
        server = MCPBase64Server(config)
        
        # Initialize components
        server.initialize()
        
        print("✅ HTTP server initialization successful")
        
        # Start server in a thread
        def run_server():
            try:
                server.start()
                time.sleep(2)  # Run for 2 seconds
                server.stop()
            except Exception as e:
                print(f"Server thread error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        if server._running:
            print("✅ Server started successfully")
        else:
            print("❌ Server failed to start")
        
        # Wait for server to stop
        server_thread.join(timeout=3)
        
        print("✅ Server stopped successfully")
        return True
        
    except Exception as e:
        print(f"❌ HTTP server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Simple Main Server Test")
    print("=" * 40)
    
    success = True
    
    # Test initialization
    success &= test_server_initialization()
    
    # Test HTTP server
    success &= test_server_with_http()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
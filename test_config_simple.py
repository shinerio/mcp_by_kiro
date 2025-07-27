#!/usr/bin/env python3
"""
Simple configuration test
"""

from config import ConfigManager

def test_config():
    print("Testing configuration system...")
    
    try:
        # Test configuration loading
        cm = ConfigManager()
        config = cm.load_config()
        
        print("✅ Configuration loaded successfully")
        print(f"Server name: {config.server.name}")
        print(f"Transport type: {config.transport.type}")
        print(f"HTTP server enabled: {config.http_server.enabled}")
        print(f"HTTP server port: {config.http_server.port}")
        print(f"Log level: {config.logging.level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    test_config()
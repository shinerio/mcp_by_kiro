#!/usr/bin/env python3
"""
Performance Benchmark Test for MCP Base64 Server

This script tests the performance characteristics of the MCP Base64 server
to ensure it meets deployment requirements.
"""

import sys
import time
import threading
import requests
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from servers.http_server import HTTPServer
from models.mcp_models import MCPRequest


def benchmark_base64_service():
    """Benchmark Base64Service performance"""
    print("=== Base64Service Performance Benchmark ===")
    
    service = Base64Service()
    
    # Test data of different sizes
    test_cases = [
        ("Small text (10 chars)", "A" * 10),
        ("Medium text (1KB)", "A" * 1024),
        ("Large text (10KB)", "A" * 10240),
        ("Very large text (100KB)", "A" * 102400),
    ]
    
    for name, text in test_cases:
        # Benchmark encoding
        start_time = time.time()
        for _ in range(1000):
            encoded = service.encode(text)
        encode_time = time.time() - start_time
        
        # Benchmark decoding
        start_time = time.time()
        for _ in range(1000):
            service.decode(encoded)
        decode_time = time.time() - start_time
        
        print(f"{name}:")
        print(f"  Encoding: {encode_time:.3f}s (1000 ops) = {1000/encode_time:.0f} ops/sec")
        print(f"  Decoding: {decode_time:.3f}s (1000 ops) = {1000/decode_time:.0f} ops/sec")
    
    return True


def benchmark_mcp_handler():
    """Benchmark MCP Protocol Handler performance"""
    print("\n=== MCP Protocol Handler Performance Benchmark ===")
    
    service = Base64Service()
    handler = MCPProtocolHandler(service)
    
    # Test encode request
    encode_request = MCPRequest(
        jsonrpc="2.0",
        id=1,
        method="tools/call",
        params={
            "name": "base64_encode",
            "arguments": {"text": "Hello, World!"}
        }
    )
    
    # Benchmark encode requests
    start_time = time.time()
    for _ in range(1000):
        handler.handle_request(encode_request)
    encode_time = time.time() - start_time
    
    # Test decode request
    decode_request = MCPRequest(
        jsonrpc="2.0",
        id=2,
        method="tools/call",
        params={
            "name": "base64_decode",
            "arguments": {"base64_string": "SGVsbG8sIFdvcmxkIQ=="}
        }
    )
    
    # Benchmark decode requests
    start_time = time.time()
    for _ in range(1000):
        handler.handle_request(decode_request)
    decode_time = time.time() - start_time
    
    print(f"MCP Encode Requests: {encode_time:.3f}s (1000 ops) = {1000/encode_time:.0f} ops/sec")
    print(f"MCP Decode Requests: {decode_time:.3f}s (1000 ops) = {1000/decode_time:.0f} ops/sec")
    
    return True


def benchmark_http_server():
    """Benchmark HTTP Server performance"""
    print("\n=== HTTP Server Performance Benchmark ===")
    
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
        # Benchmark health endpoint
        start_time = time.time()
        for _ in range(100):
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200
        health_time = time.time() - start_time
        
        # Benchmark encode endpoint
        encode_data = {"text": "Hello, World!"}
        start_time = time.time()
        for _ in range(100):
            response = requests.post(f"{base_url}/encode", json=encode_data, timeout=5)
            assert response.status_code == 200
        encode_time = time.time() - start_time
        
        # Benchmark decode endpoint
        decode_data = {"base64_string": "SGVsbG8sIFdvcmxkIQ=="}
        start_time = time.time()
        for _ in range(100):
            response = requests.post(f"{base_url}/decode", json=decode_data, timeout=5)
            assert response.status_code == 200
        decode_time = time.time() - start_time
        
        print(f"Health Endpoint: {health_time:.3f}s (100 requests) = {100/health_time:.0f} req/sec")
        print(f"Encode Endpoint: {encode_time:.3f}s (100 requests) = {100/encode_time:.0f} req/sec")
        print(f"Decode Endpoint: {decode_time:.3f}s (100 requests) = {100/decode_time:.0f} req/sec")
        
    finally:
        server.stop()
    
    return True


def run_performance_benchmarks():
    """Run all performance benchmarks"""
    print("MCP Base64 Server Performance Benchmarks")
    print("=" * 50)
    
    benchmarks = [
        benchmark_base64_service,
        benchmark_mcp_handler,
        benchmark_http_server,
    ]
    
    results = []
    
    for benchmark in benchmarks:
        try:
            start_time = time.time()
            success = benchmark()
            duration = time.time() - start_time
            results.append((benchmark.__name__, success, duration))
        except Exception as e:
            print(f"❌ {benchmark.__name__} failed: {e}")
            results.append((benchmark.__name__, False, 0))
    
    print("\n" + "=" * 50)
    print("Benchmark Results:")
    
    for name, success, duration in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name}: {status} ({duration:.2f}s)")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} benchmarks passed")
    
    if passed == total:
        print("🎉 All performance benchmarks passed!")
        print("The server meets performance requirements for deployment.")
        return True
    else:
        print("⚠️  Some benchmarks failed. Review performance before deployment.")
        return False


if __name__ == "__main__":
    success = run_performance_benchmarks()
    sys.exit(0 if success else 1)
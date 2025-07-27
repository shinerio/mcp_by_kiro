#!/usr/bin/env python3
"""
MCP客户端集成示例

本示例展示如何在Python应用中集成MCP Base64服务器，
包括连接建立、工具调用和错误处理的完整流程。
"""

import asyncio
import json
import sys
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MCPRequest:
    """MCP请求数据结构"""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Dict[str, Any] = None
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        data = {
            "jsonrpc": self.jsonrpc,
            "method": self.method
        }
        if self.id is not None:
            data["id"] = self.id
        if self.params:
            data["params"] = self.params
        return json.dumps(data)


@dataclass
class MCPResponse:
    """MCP响应数据结构"""
    jsonrpc: str
    id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """从JSON字符串创建响应对象"""
        data = json.loads(json_str)
        return cls(
            jsonrpc=data["jsonrpc"],
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error")
        )


class MCPBase64Client:
    """
    MCP Base64客户端
    
    提供与MCP Base64服务器通信的高级接口，
    支持stdio和HTTP两种传输方式。
    """
    
    def __init__(self, transport_type: str = "stdio", **kwargs):
        """
        初始化MCP客户端
        
        Args:
            transport_type: 传输类型 ("stdio" 或 "http")
            **kwargs: 传输特定的参数
        """
        self.transport_type = transport_type
        self.process = None
        self.request_id = 0
        self.initialized = False
        
        if transport_type == "stdio":
            self.server_command = kwargs.get("server_command", [
                sys.executable, "main.py", "--transport", "stdio"
            ])
        elif transport_type == "http":
            self.base_url = kwargs.get("base_url", "http://localhost:3000")
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
    
    async def connect(self) -> None:
        """建立与MCP服务器的连接"""
        if self.transport_type == "stdio":
            await self._connect_stdio()
        elif self.transport_type == "http":
            await self._connect_http()
        
        # 执行MCP握手
        await self._initialize()
    
    async def _connect_stdio(self) -> None:
        """建立stdio连接"""
        print("🔌 Connecting to MCP server via stdio...")
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            print("✅ Stdio connection established")
        except Exception as e:
            raise ConnectionError(f"Failed to start MCP server: {e}")
    
    async def _connect_http(self) -> None:
        """建立HTTP连接"""
        print(f"🔌 Connecting to MCP server via HTTP: {self.base_url}")
        # HTTP连接在实际请求时建立
        print("✅ HTTP connection configured")
    
    async def _initialize(self) -> None:
        """执行MCP初始化握手"""
        print("🤝 Initializing MCP connection...")
        
        # 发送initialize请求
        init_request = MCPRequest(
            id=self._next_id(),
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {
                    "name": "mcp-base64-client-example",
                    "version": "1.0.0"
                }
            }
        )
        
        response = await self._send_request(init_request)
        
        if response.error:
            raise Exception(f"Initialization failed: {response.error}")
        
        # 发送initialized通知
        initialized_notification = MCPRequest(
            method="notifications/initialized"
        )
        
        await self._send_notification(initialized_notification)
        
        self.initialized = True
        print("✅ MCP connection initialized successfully")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        if not self.initialized:
            raise RuntimeError("Client not initialized. Call connect() first.")
        
        print("📋 Fetching available tools...")
        
        request = MCPRequest(
            id=self._next_id(),
            method="tools/list"
        )
        
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to list tools: {response.error}")
        
        tools = response.result.get("tools", [])
        print(f"✅ Found {len(tools)} available tools")
        
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        调用指定工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            str: 工具执行结果
        """
        if not self.initialized:
            raise RuntimeError("Client not initialized. Call connect() first.")
        
        print(f"🔧 Calling tool '{name}' with arguments: {arguments}")
        
        request = MCPRequest(
            id=self._next_id(),
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments
            }
        )
        
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Tool call failed: {response.error}")
        
        # 提取结果文本
        content = response.result.get("content", [])
        if content and len(content) > 0:
            result = content[0].get("text", "")
            print(f"✅ Tool '{name}' executed successfully")
            return result
        else:
            raise Exception("No result content returned")
    
    async def encode_text(self, text: str) -> str:
        """编码文本为base64"""
        return await self.call_tool("base64_encode", {"text": text})
    
    async def decode_base64(self, base64_string: str) -> str:
        """解码base64为文本"""
        return await self.call_tool("base64_decode", {"base64_string": base64_string})
    
    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """发送请求并等待响应"""
        if self.transport_type == "stdio":
            return await self._send_request_stdio(request)
        elif self.transport_type == "http":
            return await self._send_request_http(request)
    
    async def _send_notification(self, notification: MCPRequest) -> None:
        """发送通知（无需响应）"""
        if self.transport_type == "stdio":
            await self._send_notification_stdio(notification)
        elif self.transport_type == "http":
            await self._send_notification_http(notification)
    
    async def _send_request_stdio(self, request: MCPRequest) -> MCPResponse:
        """通过stdio发送请求"""
        if not self.process:
            raise RuntimeError("Stdio connection not established")
        
        # 发送请求
        request_json = request.to_json() + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # 读取响应
        response_line = await self.process.stdout.readline()
        response_json = response_line.decode().strip()
        
        return MCPResponse.from_json(response_json)
    
    async def _send_notification_stdio(self, notification: MCPRequest) -> None:
        """通过stdio发送通知"""
        if not self.process:
            raise RuntimeError("Stdio connection not established")
        
        notification_json = notification.to_json() + "\n"
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()
    
    async def _send_request_http(self, request: MCPRequest) -> MCPResponse:
        """通过HTTP发送请求"""
        # 这里应该实现HTTP传输逻辑
        # 为了简化示例，这里只是占位符
        raise NotImplementedError("HTTP transport not implemented in this example")
    
    async def _send_notification_http(self, notification: MCPRequest) -> None:
        """通过HTTP发送通知"""
        # HTTP传输通常不需要单独的通知机制
        pass
    
    def _next_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id += 1
        return self.request_id
    
    async def close(self) -> None:
        """关闭连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("🔌 Connection closed")


async def basic_usage_example():
    """基础使用示例"""
    print("=" * 60)
    print("🚀 MCP Base64 Client - Basic Usage Example")
    print("=" * 60)
    
    client = MCPBase64Client(transport_type="stdio")
    
    try:
        # 连接到服务器
        await client.connect()
        
        # 获取可用工具
        tools = await client.list_tools()
        
        # 编码示例
        print("\n📝 Encoding Examples:")
        test_texts = [
            "Hello, World!",
            "MCP Base64 Server",
            "🚀 Unicode support! 中文测试",
            ""  # 空字符串测试
        ]
        
        for text in test_texts:
            try:
                encoded = await client.encode_text(text)
                print(f"  Input:  '{text}'")
                print(f"  Output: '{encoded}'")
                print()
            except Exception as e:
                print(f"  Error encoding '{text}': {e}")
        
        # 解码示例
        print("\n🔓 Decoding Examples:")
        test_base64 = [
            "SGVsbG8sIFdvcmxkIQ==",
            "TUNQIEJhc2U2NCBTZXJ2ZXI=",
            "8J+agCBVbmljb2RlIHN1cHBvcnQhIOS4reaWhea1i+ivlQ==",
            ""  # 空字符串测试
        ]
        
        for base64_str in test_base64:
            try:
                decoded = await client.decode_base64(base64_str)
                print(f"  Input:  '{base64_str}'")
                print(f"  Output: '{decoded}'")
                print()
            except Exception as e:
                print(f"  Error decoding '{base64_str}': {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


async def error_handling_example():
    """错误处理示例"""
    print("=" * 60)
    print("⚠️  MCP Base64 Client - Error Handling Example")
    print("=" * 60)
    
    client = MCPBase64Client(transport_type="stdio")
    
    try:
        await client.connect()
        
        # 测试无效的base64字符串
        print("\n🔍 Testing invalid base64 strings:")
        invalid_base64_strings = [
            "invalid-base64!",
            "SGVsbG8=invalid",
            "not-base64-at-all",
            "SGVsbG8"  # 缺少填充
        ]
        
        for invalid_str in invalid_base64_strings:
            try:
                result = await client.decode_base64(invalid_str)
                print(f"  ❌ Unexpected success for '{invalid_str}': {result}")
            except Exception as e:
                print(f"  ✅ Expected error for '{invalid_str}': {e}")
        
        # 测试非常大的输入
        print("\n📏 Testing large input:")
        large_text = "A" * 1000000  # 1MB文本
        try:
            encoded = await client.encode_text(large_text)
            print(f"  ✅ Large text encoded successfully (length: {len(encoded)})")
        except Exception as e:
            print(f"  ⚠️  Large text encoding failed: {e}")
        
        # 测试不存在的工具
        print("\n🔧 Testing non-existent tool:")
        try:
            await client.call_tool("non_existent_tool", {"param": "value"})
        except Exception as e:
            print(f"  ✅ Expected error for non-existent tool: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


async def batch_processing_example():
    """批量处理示例"""
    print("=" * 60)
    print("📦 MCP Base64 Client - Batch Processing Example")
    print("=" * 60)
    
    client = MCPBase64Client(transport_type="stdio")
    
    try:
        await client.connect()
        
        # 批量编码
        print("\n📝 Batch encoding:")
        texts_to_encode = [
            f"Message {i}: Hello from batch processing!"
            for i in range(1, 11)
        ]
        
        encoded_results = []
        for i, text in enumerate(texts_to_encode, 1):
            try:
                encoded = await client.encode_text(text)
                encoded_results.append(encoded)
                print(f"  {i:2d}. Encoded: {text[:30]}... -> {encoded[:30]}...")
            except Exception as e:
                print(f"  {i:2d}. Error: {e}")
        
        # 批量解码
        print(f"\n🔓 Batch decoding ({len(encoded_results)} items):")
        for i, encoded in enumerate(encoded_results, 1):
            try:
                decoded = await client.decode_base64(encoded)
                print(f"  {i:2d}. Decoded: {encoded[:30]}... -> {decoded[:30]}...")
            except Exception as e:
                print(f"  {i:2d}. Error: {e}")
        
        # 性能测试
        print("\n⏱️  Performance test:")
        import time
        
        start_time = time.time()
        for _ in range(100):
            await client.encode_text("Performance test message")
        end_time = time.time()
        
        print(f"  100 encode operations took {end_time - start_time:.2f} seconds")
        print(f"  Average: {(end_time - start_time) * 10:.2f} ms per operation")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


async def file_processing_example():
    """文件处理示例"""
    print("=" * 60)
    print("📁 MCP Base64 Client - File Processing Example")
    print("=" * 60)
    
    client = MCPBase64Client(transport_type="stdio")
    
    try:
        await client.connect()
        
        # 创建示例文件
        test_file = Path("test_file.txt")
        test_content = """This is a test file for MCP Base64 encoding.
It contains multiple lines of text.
Including some special characters: !@#$%^&*()
And Unicode: 你好世界 🌍"""
        
        test_file.write_text(test_content, encoding='utf-8')
        print(f"📄 Created test file: {test_file}")
        
        # 读取并编码文件内容
        file_content = test_file.read_text(encoding='utf-8')
        print(f"📖 File content ({len(file_content)} characters):")
        print(f"  {file_content[:100]}...")
        
        encoded_content = await client.encode_text(file_content)
        print(f"\n🔐 Encoded content ({len(encoded_content)} characters):")
        print(f"  {encoded_content[:100]}...")
        
        # 保存编码结果
        encoded_file = Path("test_file_encoded.txt")
        encoded_file.write_text(encoded_content, encoding='utf-8')
        print(f"💾 Saved encoded content to: {encoded_file}")
        
        # 读取并解码
        encoded_from_file = encoded_file.read_text(encoding='utf-8')
        decoded_content = await client.decode_base64(encoded_from_file)
        
        # 验证结果
        if decoded_content == file_content:
            print("✅ File encoding/decoding successful - content matches!")
        else:
            print("❌ File encoding/decoding failed - content mismatch!")
        
        # 保存解码结果
        decoded_file = Path("test_file_decoded.txt")
        decoded_file.write_text(decoded_content, encoding='utf-8')
        print(f"💾 Saved decoded content to: {decoded_file}")
        
        # 清理临时文件
        test_file.unlink()
        encoded_file.unlink()
        decoded_file.unlink()
        print("🧹 Cleaned up temporary files")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


async def main():
    """主函数 - 运行所有示例"""
    print("🎯 MCP Base64 Client Integration Examples")
    print("This script demonstrates various ways to integrate with MCP Base64 Server")
    print()
    
    examples = [
        ("Basic Usage", basic_usage_example),
        ("Error Handling", error_handling_example),
        ("Batch Processing", batch_processing_example),
        ("File Processing", file_processing_example)
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
            print("\n" + "✅ " + "=" * 58)
            print(f"✅ {name} example completed successfully")
            print("✅ " + "=" * 58)
        except Exception as e:
            print("\n" + "❌ " + "=" * 58)
            print(f"❌ {name} example failed: {e}")
            print("❌ " + "=" * 58)
        
        print("\n" * 2)
    
    print("🎉 All examples completed!")
    print("\nNext steps:")
    print("1. Try modifying the examples to suit your needs")
    print("2. Integrate the client code into your application")
    print("3. Explore the HTTP transport option")
    print("4. Check out the MCP Inspector for debugging")


if __name__ == "__main__":
    # 确保在正确的目录中运行
    if not Path("main.py").exists():
        print("❌ Error: Please run this script from the mcp-base64-server directory")
        print("   The main.py file should be in the current directory")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
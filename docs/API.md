# MCP Base64 Server API 文档

本文档详细描述了MCP Base64 Server提供的所有API接口，包括MCP协议接口和HTTP REST API接口。

## 目录

- [MCP协议API](#mcp协议api)
- [HTTP REST API](#http-rest-api)
- [错误处理](#错误处理)
- [认证和安全](#认证和安全)
- [速率限制](#速率限制)
- [SDK和客户端库](#sdk和客户端库)

## MCP协议API

MCP (Model Context Protocol) 是基于JSON-RPC 2.0的协议，用于AI代理与工具服务器之间的通信。

### 协议握手

#### initialize

初始化MCP连接。

**请求:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "clientInfo": {
      "name": "example-client",
      "version": "1.0.0"
    }
  }
}
```

**响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {
        "listChanged": false
      }
    },
    "serverInfo": {
      "name": "mcp-base64-server",
      "version": "1.0.0"
    }
  }
}
```

#### initialized

确认初始化完成。

**通知:**
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

### 工具管理

#### tools/list

获取可用工具列表。

**请求:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

**响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "base64_encode",
        "description": "将文本字符串编码为base64格式",
        "inputSchema": {
          "type": "object",
          "properties": {
            "text": {
              "type": "string",
              "description": "要编码的文本字符串"
            }
          },
          "required": ["text"]
        }
      },
      {
        "name": "base64_decode",
        "description": "将base64字符串解码为文本",
        "inputSchema": {
          "type": "object",
          "properties": {
            "base64_string": {
              "type": "string",
              "description": "要解码的base64字符串"
            }
          },
          "required": ["base64_string"]
        }
      }
    ]
  }
}
```

#### tools/call

调用指定工具。

**base64_encode 请求:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "base64_encode",
    "arguments": {
      "text": "Hello, World!"
    }
  }
}
```

**base64_encode 响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "SGVsbG8sIFdvcmxkIQ=="
      }
    ],
    "isError": false
  }
}
```

**base64_decode 请求:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "base64_decode",
    "arguments": {
      "base64_string": "SGVsbG8sIFdvcmxkIQ=="
    }
  }
}
```

**base64_decode 响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Hello, World!"
      }
    ],
    "isError": false
  }
}
```

### 工具详细说明

#### base64_encode

**功能**: 将UTF-8文本字符串编码为base64格式

**参数**:
- `text` (string, required): 要编码的文本字符串
  - 最大长度: 1MB (1,048,576 字符)
  - 支持所有UTF-8字符
  - 空字符串将返回空的base64字符串

**返回值**:
- 成功: base64编码的字符串
- 失败: 错误信息

**示例**:
```json
// 输入: "Hello, 世界!"
// 输出: "SGVsbG8sIOS4lueVjCE="

// 输入: ""
// 输出: ""

// 输入: "🚀 Rocket"
// 输出: "8J+agCBSb2NrZXQ="
```

**性能特征**:
- 时间复杂度: O(n)，其中n是输入文本长度
- 内存使用: 约为输入大小的1.33倍
- 平均处理时间: < 1ms (1KB文本)

#### base64_decode

**功能**: 将base64字符串解码为UTF-8文本

**参数**:
- `base64_string` (string, required): 要解码的base64字符串
  - 必须是有效的base64格式
  - 支持标准base64字符集 (A-Z, a-z, 0-9, +, /, =)
  - 自动忽略空白字符

**返回值**:
- 成功: 解码后的UTF-8文本字符串
- 失败: 错误信息

**示例**:
```json
// 输入: "SGVsbG8sIOS4lueVjCE="
// 输出: "Hello, 世界!"

// 输入: ""
// 输出: ""

// 输入: "8J+agCBSb2NrZXQ="
// 输出: "🚀 Rocket"
```

**错误情况**:
- 无效的base64字符
- 不正确的填充
- 解码后的数据不是有效的UTF-8

## HTTP REST API

HTTP REST API提供了简单的HTTP接口来访问base64编解码功能。

### 基础信息

- **Base URL**: `http://localhost:8080` (默认)
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 端点列表

#### POST /encode

编码文本为base64格式。

**请求**:
```http
POST /encode HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "text": "Hello, World!"
}
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "result": "SGVsbG8sIFdvcmxkIQ==",
  "metadata": {
    "input_length": 13,
    "output_length": 20,
    "processing_time_ms": 0.5
  }
}
```

**cURL示例**:
```bash
curl -X POST http://localhost:8080/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, World!"}'
```

#### POST /decode

解码base64字符串为文本。

**请求**:
```http
POST /decode HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "base64_string": "SGVsbG8sIFdvcmxkIQ=="
}
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "result": "Hello, World!",
  "metadata": {
    "input_length": 20,
    "output_length": 13,
    "processing_time_ms": 0.3
  }
}
```

**cURL示例**:
```bash
curl -X POST http://localhost:8080/decode \
  -H "Content-Type: application/json" \
  -d '{"base64_string": "SGVsbG8sIFdvcmxkIQ=="}'
```

#### GET /health

健康检查端点。

**请求**:
```http
GET /health HTTP/1.1
Host: localhost:8080
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "server": "mcp-base64-server",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime_seconds": 3600,
  "memory_usage_mb": 45.2,
  "cpu_usage_percent": 2.1
}
```

#### GET /tools

获取可用的MCP工具信息。

**请求**:
```http
GET /tools HTTP/1.1
Host: localhost:8080
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "tools": [
    {
      "name": "base64_encode",
      "description": "将文本字符串编码为base64格式",
      "inputSchema": {
        "type": "object",
        "properties": {
          "text": {
            "type": "string",
            "description": "要编码的文本字符串"
          }
        },
        "required": ["text"]
      }
    },
    {
      "name": "base64_decode",
      "description": "将base64字符串解码为文本",
      "inputSchema": {
        "type": "object",
        "properties": {
          "base64_string": {
            "type": "string",
            "description": "要解码的base64字符串"
          }
        },
        "required": ["base64_string"]
      }
    }
  ],
  "total_count": 2
}
```

#### GET /stats

获取服务器统计信息。

**请求**:
```http
GET /stats HTTP/1.1
Host: localhost:8080
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "requests": {
    "total": 1250,
    "encode": 750,
    "decode": 500,
    "success_rate": 0.996
  },
  "performance": {
    "avg_response_time_ms": 1.2,
    "p95_response_time_ms": 3.5,
    "p99_response_time_ms": 8.1
  },
  "system": {
    "uptime_seconds": 86400,
    "memory_usage_mb": 52.3,
    "cpu_usage_percent": 1.8
  },
  "errors": {
    "total": 5,
    "invalid_base64": 3,
    "encoding_error": 1,
    "decoding_error": 1
  }
}
```

#### OPTIONS /*

CORS预检请求处理。

**请求**:
```http
OPTIONS /encode HTTP/1.1
Host: localhost:8080
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type
```

**响应**:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

### 批量操作

#### POST /batch/encode

批量编码多个文本。

**请求**:
```http
POST /batch/encode HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "texts": [
    "Hello",
    "World",
    "Base64"
  ]
}
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "results": [
    {
      "input": "Hello",
      "output": "SGVsbG8=",
      "success": true
    },
    {
      "input": "World",
      "output": "V29ybGQ=",
      "success": true
    },
    {
      "input": "Base64",
      "output": "QmFzZTY0",
      "success": true
    }
  ],
  "metadata": {
    "total_items": 3,
    "successful_items": 3,
    "failed_items": 0,
    "processing_time_ms": 2.1
  }
}
```

#### POST /batch/decode

批量解码多个base64字符串。

**请求**:
```http
POST /batch/decode HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "base64_strings": [
    "SGVsbG8=",
    "V29ybGQ=",
    "QmFzZTY0"
  ]
}
```

**响应**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "results": [
    {
      "input": "SGVsbG8=",
      "output": "Hello",
      "success": true
    },
    {
      "input": "V29ybGQ=",
      "output": "World",
      "success": true
    },
    {
      "input": "QmFzZTY0",
      "output": "Base64",
      "success": true
    }
  ],
  "metadata": {
    "total_items": 3,
    "successful_items": 3,
    "failed_items": 0,
    "processing_time_ms": 1.8
  }
}
```

## 错误处理

### MCP协议错误

MCP协议使用标准的JSON-RPC 2.0错误格式：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -1001,
    "message": "Invalid base64 string",
    "data": {
      "input": "invalid-base64!",
      "position": 12,
      "character": "!"
    }
  }
}
```

#### 错误代码表

| 代码 | 名称 | 描述 | 解决方案 |
|------|------|------|----------|
| -32700 | Parse Error | JSON解析错误 | 检查JSON格式 |
| -32600 | Invalid Request | 无效请求 | 检查请求结构 |
| -32601 | Method Not Found | 方法不存在 | 检查方法名称 |
| -32602 | Invalid Params | 参数无效 | 检查参数格式和类型 |
| -32603 | Internal Error | 内部错误 | 联系技术支持 |
| -1001 | Invalid Base64 | 无效base64字符串 | 检查base64格式 |
| -1002 | Encoding Error | 编码失败 | 检查输入文本 |
| -1003 | Decoding Error | 解码失败 | 检查base64字符串 |
| -1004 | Input Too Large | 输入过大 | 减少输入大小 |
| -1005 | Rate Limit Exceeded | 超过速率限制 | 降低请求频率 |

### HTTP API错误

HTTP API使用标准HTTP状态码和JSON错误响应：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_BASE64",
    "message": "Invalid base64 string: contains invalid characters",
    "details": {
      "input": "invalid-base64!",
      "invalid_characters": ["!"],
      "position": 12
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

#### HTTP状态码

| 状态码 | 描述 | 常见原因 |
|--------|------|----------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求错误 | 参数格式错误、缺少必需参数 |
| 401 | 未授权 | 缺少或无效的认证信息 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 未找到 | 端点不存在 |
| 405 | 方法不允许 | HTTP方法不支持 |
| 413 | 请求实体过大 | 输入数据超过限制 |
| 429 | 请求过多 | 超过速率限制 |
| 500 | 服务器错误 | 内部处理错误 |
| 503 | 服务不可用 | 服务器过载或维护 |

### 错误处理最佳实践

#### 客户端错误处理

```python
import requests
import json

def encode_text(text: str) -> str:
    """安全的文本编码函数"""
    try:
        response = requests.post(
            'http://localhost:8080/encode',
            json={'text': text},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                return data['result']
            else:
                raise ValueError(f"Encoding failed: {data['error']['message']}")
        
        elif response.status_code == 400:
            error_data = response.json()
            raise ValueError(f"Invalid input: {error_data['error']['message']}")
        
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded, please try again later")
        
        else:
            response.raise_for_status()
            
    except requests.exceptions.Timeout:
        raise Exception("Request timeout, please try again")
    
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to server")
    
    except json.JSONDecodeError:
        raise Exception("Invalid response format")
```

#### 重试机制

```python
import time
import random
from typing import Callable, Any

def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Any:
    """带指数退避的重试机制"""
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            # 计算延迟时间（指数退避 + 随机抖动）
            delay = min(
                base_delay * (2 ** attempt) + random.uniform(0, 1),
                max_delay
            )
            
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

# 使用示例
result = retry_with_backoff(
    lambda: encode_text("Hello, World!")
)
```

## 认证和安全

### API密钥认证（可选）

如果启用了认证，需要在请求头中包含API密钥：

```http
POST /encode HTTP/1.1
Host: localhost:8080
Content-Type: application/json
Authorization: Bearer your-api-key-here

{
  "text": "Hello, World!"
}
```

### HTTPS支持

生产环境建议使用HTTPS：

```yaml
# config.yaml
http_server:
  enabled: true
  host: "0.0.0.0"
  port: 8443
  ssl:
    enabled: true
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
```

### 输入验证

服务器对所有输入进行严格验证：

- **文本长度限制**: 最大1MB
- **Base64格式验证**: 严格的字符集检查
- **UTF-8编码验证**: 确保文本有效性
- **SQL注入防护**: 虽然不使用数据库，但仍进行基础防护
- **XSS防护**: 对输出进行适当转义

### 安全头部

服务器自动添加安全相关的HTTP头部：

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## 速率限制

### 默认限制

- **每IP每分钟**: 100个请求
- **每IP每小时**: 1000个请求
- **每IP每天**: 10000个请求

### 限制头部

响应中包含速率限制信息：

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 60
```

### 超出限制的响应

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60

{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 100,
      "window_seconds": 60,
      "retry_after_seconds": 60
    }
  }
}
```

## SDK和客户端库

### Python SDK

```python
from mcp_base64_client import Base64Client

# 初始化客户端
client = Base64Client(base_url="http://localhost:8080")

# 编码文本
encoded = client.encode("Hello, World!")
print(encoded)  # SGVsbG8sIFdvcmxkIQ==

# 解码base64
decoded = client.decode("SGVsbG8sIFdvcmxkIQ==")
print(decoded)  # Hello, World!

# 批量操作
results = client.batch_encode(["Hello", "World"])
print(results)  # [{"input": "Hello", "output": "SGVsbG8=", "success": true}, ...]
```

### JavaScript SDK

```javascript
import { Base64Client } from 'mcp-base64-client';

// 初始化客户端
const client = new Base64Client('http://localhost:8080');

// 编码文本
const encoded = await client.encode('Hello, World!');
console.log(encoded); // SGVsbG8sIFdvcmxkIQ==

// 解码base64
const decoded = await client.decode('SGVsbG8sIFdvcmxkIQ==');
console.log(decoded); // Hello, World!

// 错误处理
try {
  const result = await client.decode('invalid-base64!');
} catch (error) {
  console.error('Decoding failed:', error.message);
}
```

### MCP客户端集成

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 连接到MCP服务器
    server_params = StdioServerParameters(
        command="python",
        args=["/path/to/mcp-base64-server/main.py", "--transport", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            
            # 获取可用工具
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools])
            
            # 调用base64编码工具
            result = await session.call_tool("base64_encode", {"text": "Hello, MCP!"})
            print("Encoded:", result.content[0].text)
            
            # 调用base64解码工具
            result = await session.call_tool("base64_decode", {"base64_string": "SGVsbG8sIE1DUCE="})
            print("Decoded:", result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
```

## 性能优化

### 缓存策略

服务器实现了智能缓存来提高性能：

```python
# 启用缓存
client = Base64Client(
    base_url="http://localhost:8080",
    cache_enabled=True,
    cache_ttl=300  # 5分钟
)
```

### 连接池

使用连接池来提高并发性能：

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置连接池
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=3, backoff_factor=0.3)
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 使用会话发送请求
response = session.post(
    'http://localhost:8080/encode',
    json={'text': 'Hello, World!'}
)
```

### 异步处理

对于高并发场景，推荐使用异步客户端：

```python
import asyncio
import aiohttp

async def encode_async(session, text):
    """异步编码函数"""
    async with session.post(
        'http://localhost:8080/encode',
        json={'text': text}
    ) as response:
        data = await response.json()
        return data['result']

async def main():
    async with aiohttp.ClientSession() as session:
        # 并发处理多个请求
        tasks = [
            encode_async(session, f"Text {i}")
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks)
        print(f"Processed {len(results)} items")

asyncio.run(main())
```

---

本API文档涵盖了MCP Base64 Server的所有接口和功能。如有疑问或需要更多信息，请参考[README.md](../README.md)或联系技术支持。
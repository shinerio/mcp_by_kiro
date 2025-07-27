# MCP Inspector 使用教程

MCP Inspector是官方提供的调试和测试工具，用于与MCP服务器交互。本教程将详细介绍如何使用MCP Inspector来调试和测试MCP Base64服务器。

## 目录

- [什么是MCP Inspector](#什么是mcp-inspector)
- [安装和设置](#安装和设置)
- [连接到服务器](#连接到服务器)
- [界面介绍](#界面介绍)
- [测试工具功能](#测试工具功能)
- [调试技巧](#调试技巧)
- [常见问题](#常见问题)
- [高级用法](#高级用法)

## 什么是MCP Inspector

MCP Inspector是一个Web界面工具，提供以下功能：

- 🔍 **工具发现**: 自动发现和列出MCP服务器提供的所有工具
- 🧪 **交互式测试**: 通过图形界面测试工具调用
- 📊 **请求/响应查看**: 实时查看MCP消息的详细内容
- 🐛 **调试支持**: 帮助识别连接和协议问题
- 📝 **Schema验证**: 验证工具参数是否符合定义的schema

## 安装和设置

### 1. 安装MCP Inspector

```bash
# 使用npm安装（推荐）
npm install -g @modelcontextprotocol/inspector

# 或使用npx（无需全局安装）
npx @modelcontextprotocol/inspector
```

### 2. 验证安装

```bash
# 检查版本
mcp-inspector --version

# 查看帮助
mcp-inspector --help
```

### 3. 启动MCP Base64服务器

在使用Inspector之前，需要先启动MCP服务器：

#### 方式1: HTTP模式（推荐用于Inspector）

```bash
# 启动HTTP模式的MCP服务器
python main.py --transport http --http-port 3000

# 输出应该显示：
# 📡 MCP Transport (HTTP):
#   - URL: http://localhost:3000
#   - Endpoint: http://localhost:3000/mcp
```

#### 方式2: Stdio模式

```bash
# 启动stdio模式（需要特殊配置）
python main.py --transport stdio
```

## 连接到服务器

### HTTP连接（推荐）

1. **启动Inspector**:
   ```bash
   mcp-inspector
   ```

2. **在浏览器中打开**: http://localhost:8080

3. **输入服务器URL**: `http://localhost:3000/mcp`

4. **点击"Connect"按钮**

### Stdio连接

1. **启动Inspector并指定命令**:
   ```bash
   mcp-inspector stdio python main.py --transport stdio
   ```

2. **在浏览器中打开**: http://localhost:8080

## 界面介绍

### 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Inspector                        │
├─────────────────────────────────────────────────────────┤
│ Connection Status: ● Connected to localhost:3000       │
├─────────────────────────────────────────────────────────┤
│ Tools (2)                          │ Messages           │
│ ├─ base64_encode                   │ ┌─────────────────┐ │
│ │  └─ Encode text to base64        │ │ Request/Response│ │
│ └─ base64_decode                   │ │ Details         │ │
│    └─ Decode base64 to text        │ │                 │ │
├─────────────────────────────────────┤ │                 │ │
│ Tool Call Interface                 │ │                 │ │
│ ┌─────────────────────────────────┐ │ │                 │ │
│ │ Selected Tool: base64_encode    │ │ │                 │ │
│ │ Parameters:                     │ │ │                 │ │
│ │ text: [input field]             │ │ │                 │ │
│ │ [Call Tool] [Clear]             │ │ │                 │ │
│ └─────────────────────────────────┘ │ └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 界面组件说明

1. **连接状态栏**: 显示与MCP服务器的连接状态
2. **工具列表**: 显示所有可用工具及其描述
3. **工具调用界面**: 用于输入参数和调用工具
4. **消息面板**: 显示详细的请求/响应消息

## 测试工具功能

### 测试base64_encode工具

1. **选择工具**: 在左侧工具列表中点击`base64_encode`

2. **输入参数**:
   ```
   text: Hello, World!
   ```

3. **调用工具**: 点击"Call Tool"按钮

4. **查看结果**: 在消息面板中查看响应
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
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

### 测试base64_decode工具

1. **选择工具**: 点击`base64_decode`

2. **输入参数**:
   ```
   base64_string: SGVsbG8sIFdvcmxkIQ==
   ```

3. **调用工具**: 点击"Call Tool"

4. **验证结果**: 应该返回`Hello, World!`

### 测试用例集合

以下是一些推荐的测试用例：

#### 基础功能测试

| 测试类型 | 工具 | 输入 | 期望输出 |
|---------|------|------|----------|
| 简单文本 | base64_encode | `Hello` | `SGVsbG8=` |
| 空字符串 | base64_encode | `` | `` |
| Unicode | base64_encode | `你好🌍` | `5L2g5aW98J+MjQ==` |
| 简单解码 | base64_decode | `SGVsbG8=` | `Hello` |
| 空解码 | base64_decode | `` | `` |

#### 错误处理测试

| 测试类型 | 工具 | 输入 | 期望结果 |
|---------|------|------|----------|
| 无效base64 | base64_decode | `invalid!` | 错误响应 |
| 缺少填充 | base64_decode | `SGVsbG8` | 错误响应 |
| 非法字符 | base64_decode | `SGVs bG8=` | 错误响应 |

#### 边界条件测试

| 测试类型 | 工具 | 输入 | 说明 |
|---------|------|------|------|
| 长文本 | base64_encode | 1000字符的文本 | 测试性能 |
| 特殊字符 | base64_encode | `!@#$%^&*()` | 测试特殊字符 |
| 多行文本 | base64_encode | 包含换行符的文本 | 测试格式处理 |

## 调试技巧

### 1. 查看详细消息

在消息面板中，可以查看完整的JSON-RPC消息：

**请求消息**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "base64_encode",
    "arguments": {
      "text": "Hello, World!"
    }
  }
}
```

**响应消息**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
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

### 2. 错误诊断

当工具调用失败时，查看错误详情：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
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

### 3. 性能监控

使用Inspector监控工具调用的性能：

1. **响应时间**: 查看每次调用的耗时
2. **内存使用**: 监控大数据处理时的内存占用
3. **错误率**: 统计成功和失败的调用比例

### 4. 连接问题诊断

#### 常见连接问题及解决方案

**问题1**: 无法连接到服务器
```
Error: Connection refused
```

**解决方案**:
1. 确认服务器已启动
2. 检查端口是否正确
3. 验证防火墙设置

**问题2**: 工具列表为空
```
No tools available
```

**解决方案**:
1. 检查服务器初始化是否完成
2. 验证MCP协议版本兼容性
3. 查看服务器日志

**问题3**: 工具调用超时
```
Request timeout
```

**解决方案**:
1. 检查输入数据大小
2. 增加超时设置
3. 监控服务器性能

## 常见问题

### Q1: Inspector无法发现工具

**症状**: 连接成功但工具列表为空

**排查步骤**:
1. 检查服务器日志是否有错误
2. 验证MCP协议握手是否成功
3. 确认工具注册是否正确

**解决方案**:
```bash
# 启用调试日志
python main.py --transport http --log-level DEBUG

# 查看详细的MCP消息交换
```

### Q2: 工具调用返回错误

**症状**: 工具调用失败，返回错误消息

**排查步骤**:
1. 检查参数格式是否正确
2. 验证参数类型是否匹配schema
3. 查看错误消息的详细信息

**解决方案**:
```json
// 确保参数格式正确
{
  "text": "Hello, World!"  // 字符串类型
}

// 而不是
{
  "text": 123  // 数字类型会导致错误
}
```

### Q3: 性能问题

**症状**: 工具调用响应缓慢

**排查步骤**:
1. 检查输入数据大小
2. 监控服务器资源使用
3. 分析网络延迟

**解决方案**:
```bash
# 启用性能监控
python main.py --enable-performance-monitoring

# 查看性能统计
curl http://localhost:8080/stats
```

## 高级用法

### 1. 自动化测试脚本

创建自动化测试脚本来批量测试工具：

```javascript
// inspector_automation.js
const puppeteer = require('puppeteer');

async function runAutomatedTests() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // 打开Inspector
  await page.goto('http://localhost:8080');
  
  // 连接到服务器
  await page.type('#server-url', 'http://localhost:3000/mcp');
  await page.click('#connect-button');
  
  // 等待连接建立
  await page.waitForSelector('.tool-list');
  
  // 测试base64_encode
  await page.click('[data-tool="base64_encode"]');
  await page.type('#param-text', 'Hello, World!');
  await page.click('#call-tool');
  
  // 验证结果
  const result = await page.textContent('#result');
  console.log('Encode result:', result);
  
  await browser.close();
}

runAutomatedTests();
```

### 2. 自定义Inspector配置

创建自定义配置文件：

```json
// inspector-config.json
{
  "servers": [
    {
      "name": "Base64 Server (HTTP)",
      "url": "http://localhost:3000/mcp",
      "type": "http"
    },
    {
      "name": "Base64 Server (Stdio)",
      "command": ["python", "main.py", "--transport", "stdio"],
      "type": "stdio"
    }
  ],
  "ui": {
    "theme": "dark",
    "autoConnect": true,
    "showRawMessages": true
  }
}
```

使用配置文件启动：

```bash
mcp-inspector --config inspector-config.json
```

### 3. 集成到CI/CD

在持续集成中使用Inspector进行自动化测试：

```yaml
# .github/workflows/mcp-test.yml
name: MCP Integration Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start MCP server
        run: |
          python main.py --transport http --http-port 3000 &
          sleep 5
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
      
      - name: Install MCP Inspector
        run: npm install -g @modelcontextprotocol/inspector
      
      - name: Run automated tests
        run: node inspector_automation.js
```

### 4. 性能基准测试

使用Inspector进行性能基准测试：

```javascript
// performance_benchmark.js
async function benchmarkTools() {
  const testCases = [
    { size: '1KB', text: 'A'.repeat(1024) },
    { size: '10KB', text: 'A'.repeat(10240) },
    { size: '100KB', text: 'A'.repeat(102400) },
    { size: '1MB', text: 'A'.repeat(1048576) }
  ];
  
  for (const testCase of testCases) {
    const startTime = Date.now();
    
    // 调用编码工具
    await callTool('base64_encode', { text: testCase.text });
    
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    console.log(`${testCase.size}: ${duration}ms`);
  }
}
```

## 总结

MCP Inspector是调试和测试MCP服务器的强大工具。通过本教程，你应该能够：

1. ✅ 安装和配置MCP Inspector
2. ✅ 连接到MCP Base64服务器
3. ✅ 测试所有可用工具
4. ✅ 诊断和解决常见问题
5. ✅ 使用高级功能进行自动化测试

### 下一步

- 探索其他MCP服务器和工具
- 开发自己的MCP服务器
- 集成MCP到你的AI应用中
- 贡献到MCP生态系统

### 相关资源

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP Inspector GitHub](https://github.com/modelcontextprotocol/inspector)
- [MCP Base64服务器文档](../README.md)
- [API文档](../API.md)

---

如果你在使用过程中遇到问题，请查看[故障排除指南](../README.md#故障排除)或提交Issue。
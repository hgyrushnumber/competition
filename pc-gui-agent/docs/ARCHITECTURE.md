# PC GUI Agent 架构说明

本文档详细说明 PC GUI Agent 的整体架构，包括 Python 客户端、MCP 服务器、以及它们之间的通信方式。

## 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    PC GUI Agent (Python)                    │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Orchestrator│    │   Planner    │    │   Worker     │ │
│  │  (协调器)    │───▶│  (规划器)    │───▶│  (执行器)    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                   │          │
│         │                    │                   │          │
│         ▼                    ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Reflector   │    │  ToolRegistry│    │  MCPClient   │ │
│  │  (反思器)    │    │  (工具注册表)│    │  (MCP客户端) │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │                              │
         │ stdio (JSON-RPC)             │ HTTP
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│  MCP Server      │          │  Ollama LLM      │
│  (独立进程)      │          │  (本地/远程)     │
│                  │          │                  │
│  - Puppeteer     │          │  - llama3.1      │
│  - Filesystem    │          │  - 其他模型      │
│  - 其他服务器    │          │                  │
└──────────────────┘          └──────────────────┘
```

## Python 客户端结构

### 1. PCGUIAgent（主类）

**位置：** `src/main.py`

**职责：**
- 初始化所有组件
- 管理 Agent 生命周期
- 协调各个模块

**主要组件：**
```python
class PCGUIAgent:
    - ollama_client: OllamaClient      # LLM 客户端
    - memory: Memory                   # 记忆数据库
    - tool_registry: ToolRegistry      # 工具注册表
    - mcp_client: MCPClient           # MCP 客户端（可选）
    - planner: Planner                 # 规划器
    - worker: Worker                   # 执行器
    - reflector: Reflector             # 反思器
    - orchestrator: Orchestrator       # 协调器
```

### 2. 核心组件

#### Planner（规划器）
**位置：** `src/core/planner.py`

**职责：**
- 接收用户目标
- 调用 LLM 生成执行计划
- 解析 LLM 返回的 JSON 计划
- 构建 Task 对象（包含多个 Subtask）

**工作流程：**
1. 获取可用工具列表
2. 生成规划 Prompt
3. 调用 Ollama LLM 生成计划
4. 解析 JSON 响应（支持多层修复：直接解析 → 正则修复 → LLM 修复）
5. 构建 Task 对象

#### Worker（执行器）
**位置：** `src/core/worker.py`

**职责：**
- 执行 Action（动作）
- 调用工具执行具体操作
- 处理执行结果和错误

**工作流程：**
1. 接收 Action 列表
2. 从 ToolRegistry 获取工具
3. 执行工具（支持重试）
4. 返回执行结果

#### Reflector（反思器）
**位置：** `src/core/reflector.py`

**职责：**
- 评估任务执行结果
- 分析成功/失败原因
- 提供改进建议
- 判断是否需要重新规划

#### Orchestrator（协调器）
**位置：** `src/core/orchestrator.py`

**职责：**
- 协调 Planner、Worker、Reflector
- 管理任务执行流程
- 处理任务依赖关系
- 管理任务状态

**执行流程：**
```
用户目标
  ↓
Planner.plan() → 生成 Task
  ↓
检索相似任务记忆
  ↓
循环执行 Subtask:
  ├─ 检查依赖
  ├─ Worker.execute_actions()
  ├─ 收集执行结果
  └─ Reflector.reflect()
  ↓
返回最终结果
```

### 3. 工具系统

#### ToolRegistry（工具注册表）
**位置：** `src/tools/registry.py`

**职责：**
- 注册和管理所有工具
- 提供工具查找和执行接口
- 统一工具调用接口

**工具类型：**
1. **GUI 工具**（默认工具）
   - navigate: 浏览器导航
   - click: 点击元素
   - input: 输入文本
   - scroll: 滚动页面
   - screenshot: 截图
   - wait: 等待

2. **MCP 工具**（从 MCP 服务器发现）
   - 动态注册
   - 名称前缀：`mcp_`
   - 通过 MCPClient 调用

#### MCPTool（MCP 工具包装器）
**位置：** `src/tools/mcp_tool.py`

**职责：**
- 将 MCP 工具包装为统一的工具接口
- 处理参数验证
- 调用 MCPClient 执行工具

## MCP 服务器结构

### 什么是 MCP 服务器？

MCP（Model Context Protocol）服务器是一个**独立的进程**，提供工具和资源访问能力。它通过标准协议与客户端通信，不依赖于客户端的实现语言。

### MCP 服务器的特点

1. **独立进程**：作为独立进程运行，与客户端分离
2. **语言无关**：可以用任何语言实现（Python、Node.js、Rust 等）
3. **标准协议**：使用 JSON-RPC 协议通信
4. **工具提供者**：提供各种工具（文件操作、浏览器控制、数据库操作等）

### 常见的 MCP 服务器

#### 1. Puppeteer MCP 服务器（Node.js）
**安装：**
```bash
npm install -g @modelcontextprotocol/server-puppeteer
```

**功能：**
- 浏览器控制（导航、点击、输入等）
- 页面截图
- DOM 操作
- 可以控制本地已安装的浏览器

**启动命令：**
```bash
npx -y @modelcontextprotocol/server-puppeteer
```

#### 2. Filesystem MCP 服务器（Python）
**安装：**
```bash
pip install mcp
```

**功能：**
- 文件读写
- 目录列表
- 文件系统操作

**启动命令：**
```bash
python -m mcp.server.filesystem
```

#### 3. 其他 MCP 服务器
- GitHub MCP 服务器（GitHub API 访问）
- SQLite MCP 服务器（数据库操作）
- 更多服务器：https://modelcontextprotocol.io/servers

## 通信方式

### stdio 通信（标准输入输出）

MCP 客户端和服务器通过 **stdio**（标准输入输出）进行通信。

**参考：** [MCP 官方文档 - 面向客户端开发者](https://mcp-docs.cn/quickstart/client)

```
Python 客户端                    MCP 服务器进程
     │                                │
     │  启动进程                      │
     ├───────────────────────────────▶│
     │  (spawn process)               │
     │                                │
     │  发送 JSON-RPC 请求            │
     ├───────────────────────────────▶│
     │  (stdin)                       │
     │                                │
     │  接收 JSON-RPC 响应            │
     │◀───────────────────────────────┤
     │  (stdout)                      │
     │                                │
```

### JSON-RPC 协议

所有通信都使用 JSON-RPC 2.0 协议：

**请求格式：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "navigate",
    "arguments": {
      "url": "https://example.com"
    }
  }
}
```

**响应格式：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "导航成功"
      }
    ]
  }
}
```

### 资源管理（使用 AsyncExitStack）

根据 MCP 官方文档的最佳实践，我们使用 `AsyncExitStack` 进行资源管理：

```python
# 使用 AsyncExitStack 管理资源（最佳实践）
self._exit_stack = AsyncExitStack()

# 连接时自动管理资源
stdio_transport = await self._exit_stack.enter_async_context(
    stdio_client(self._stdio_params)
)
self._session = await self._exit_stack.enter_async_context(
    ClientSession(self._read_stream, self._write_stream)
)

# 断开时自动清理（按相反顺序）
await self._exit_stack.aclose()
```

**优势：**
- 自动管理资源生命周期
- 确保资源按正确顺序清理
- 异常安全（即使出错也会清理资源）

### 通信流程示例

#### 1. 连接阶段

```python
# Python 客户端代码
client = MCPClient(
    server_command="npx -y @modelcontextprotocol/server-puppeteer",
    transport="stdio"
)

await client.connect()
```

**实际发生的过程：**
1. Python 客户端启动进程：`npx -y @modelcontextprotocol/server-puppeteer`
2. 使用 `AsyncExitStack` 管理 stdio_client 上下文
3. 建立 stdin/stdout 管道
4. 使用 `AsyncExitStack` 管理 ClientSession 上下文
5. 发送初始化请求（`initialize`）
6. 接收初始化响应
7. 发送工具列表请求（`tools/list`）
8. 接收工具列表响应

#### 2. 工具调用阶段

```python
# Python 客户端代码
result = await client.call_tool(
    name="navigate",
    arguments={"url": "https://example.com"}
)
```

**实际发生的过程：**
1. Python 客户端构建 JSON-RPC 请求
2. 通过 stdin 发送给 MCP 服务器
3. MCP 服务器（Node.js 进程）接收请求
4. MCP 服务器执行工具（调用 Puppeteer）
5. MCP 服务器构建 JSON-RPC 响应
6. 通过 stdout 发送给 Python 客户端
7. Python 客户端解析响应并返回结果

## 完整执行流程示例

### 场景：用户要求"打开浏览器搜索163邮箱"

```
1. 用户输入
   "打开浏览器搜索163邮箱"
   ↓
2. Orchestrator.execute_task()
   ↓
3. Planner.plan()
   ├─ 生成 Prompt（包含可用工具列表）
   ├─ 调用 Ollama LLM
   ├─ 接收 JSON 响应
   ├─ 解析 JSON（如果失败，尝试修复）
   └─ 构建 Task 对象
   ↓
4. Worker.execute_actions()
   ├─ 获取工具：navigate
   ├─ 检查工具类型：
   │   ├─ 如果是 GUI 工具 → 直接调用
   │   └─ 如果是 MCP 工具 → 通过 MCPClient 调用
   │
   ├─ 执行 navigate 工具：
   │   ├─ 如果是 MCP Puppeteer → 调用 MCPClient.call_tool()
   │   │   ├─ 构建 JSON-RPC 请求
   │   │   ├─ 发送到 MCP 服务器（Node.js 进程）
   │   │   ├─ MCP 服务器执行 Puppeteer 操作
   │   │   └─ 返回结果
   │   │
   │   └─ 如果不是 MCP → 使用 Playwright
   │
   └─ 返回执行结果
   ↓
5. Reflector.reflect()
   ├─ 分析执行结果
   ├─ 调用 Ollama LLM 进行反思
   └─ 返回反思结果
   ↓
6. 返回最终结果给用户
```

## 代码结构

### Python 客户端代码（全部是 Python）

```
src/
├── main.py                 # PCGUIAgent 主类
├── core/
│   ├── planner.py         # 规划器
│   ├── worker.py          # 执行器
│   ├── reflector.py       # 反思器
│   ├── orchestrator.py    # 协调器
│   └── types.py           # 类型定义
├── tools/
│   ├── registry.py       # 工具注册表
│   ├── base_tool.py      # 工具基类
│   ├── gui_tools.py      # GUI 工具实现
│   └── mcp_tool.py       # MCP 工具包装器
├── mcp/
│   └── client.py          # MCP 客户端（Python）
├── llm/
│   ├── ollama_client.py  # Ollama 客户端
│   └── prompt_templates.py # Prompt 模板
└── utils/
    └── logger.py          # 日志工具
```

### MCP 服务器（独立进程，可以是任何语言）

**Python 实现：**
- 安装：`pip install mcp`
- 启动：`python -m mcp.server.filesystem`
- 代码位置：已安装的 mcp 包中

**Node.js 实现：**
- 安装：`npm install -g @modelcontextprotocol/server-puppeteer`
- 启动：`npx -y @modelcontextprotocol/server-puppeteer`
- 代码位置：npm 全局包中

## 关键点总结

### 1. 客户端和服务器分离

- **客户端**：全部是 Python 代码，在你的项目中
- **服务器**：独立进程，可以是 Python 或 Node.js 实现
- **通信**：通过 stdio 和 JSON-RPC 协议

### 2. 你的代码仍然是纯 Python

- 所有业务逻辑都是 Python
- MCP 服务器只是外部工具提供者
- 通过标准协议调用，无需关心服务器实现语言

### 3. MCP 服务器的优势

- **功能扩展**：可以轻松添加新功能（安装新的 MCP 服务器）
- **稳定性**：npm 版本的服务器通常更稳定
- **语言无关**：可以选择最适合的服务器实现
- **标准化**：所有服务器都遵循 MCP 协议

### 4. 实际使用

**使用 npm 安装的 MCP 服务器：**
```powershell
# 1. 安装（只需要一次）
npm install -g @modelcontextprotocol/server-puppeteer

# 2. 设置环境变量
$env:MCP_SERVER_COMMAND = "npx -y @modelcontextprotocol/server-puppeteer"

# 3. 运行 Python 代码（完全不变）
python gui_main.py
```

**你的 Python 代码：**
```python
# 完全不需要改变
from src.main import create_agent

agent = create_agent()
await agent.initialize()
result = await agent.execute_task("打开浏览器搜索163邮箱")
```

## 架构优势

1. **解耦**：客户端和服务器完全分离，可以独立更新
2. **灵活性**：可以选择不同的 MCP 服务器实现
3. **可扩展性**：通过安装新的 MCP 服务器添加新功能
4. **标准化**：使用标准协议，兼容性好
5. **语言无关**：客户端可以用 Python，服务器可以用任何语言

## 总结

- ✅ **你的代码**：全部是 Python，在 `src/` 目录下
- ✅ **MCP 服务器**：独立进程，可以是 Python 或 Node.js
- ✅ **通信方式**：stdio + JSON-RPC 协议
- ✅ **无需修改代码**：使用 npm 安装的 MCP 服务器时，只需设置环境变量
- ✅ **完全兼容**：Python 客户端可以调用任何语言实现的 MCP 服务器


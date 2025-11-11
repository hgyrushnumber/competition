# MCP服务器下载和安装指南

本文档说明如何下载和安装真实的MCP（Model Context Protocol）服务器。

## 什么是MCP服务器

MCP服务器是实现了Model Context Protocol标准的服务器，为LLM提供工具和资源访问能力。真实的MCP服务器通常提供更完整的功能和更好的稳定性。

## 安装方法

### 方法1：使用Python MCP包（推荐）

这是最简单的方法，适合Python用户。

#### 步骤1：安装MCP包

```bash
pip install mcp
```

或者使用uv（更快的包管理器）：

```bash
# 安装uv（如果还没有）
# Windows PowerShell:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 使用uv安装MCP
uv pip install mcp
```

#### 步骤2：配置环境变量

**Windows PowerShell**：
```powershell
# 文件系统服务器
$env:MCP_SERVER_COMMAND="python -m mcp.server.filesystem"

# 或者使用其他服务器（如果可用）
# $env:MCP_SERVER_COMMAND="python -m mcp.server.github"
```

**Linux/Mac**：
```bash
# 文件系统服务器
export MCP_SERVER_COMMAND="python -m mcp.server.filesystem"

# 或者使用其他服务器（如果可用）
# export MCP_SERVER_COMMAND="python -m mcp.server.github"
```

#### 步骤3：验证安装

运行测试脚本验证MCP服务器是否正常工作：

```bash
python examples/test_mcp.py
```

### 方法2：使用npm包

适合Node.js用户或需要使用官方MCP服务器实现。

#### 步骤1：安装Node.js和npm

如果还没有安装Node.js，请从 [Node.js官网](https://nodejs.org/) 下载并安装。

#### 步骤2：安装MCP服务器包

```bash
# 安装文件系统服务器
npm install -g @modelcontextprotocol/server-filesystem

# 或者安装其他服务器
# npm install -g @modelcontextprotocol/server-github
# npm install -g @modelcontextprotocol/server-sqlite
```

#### 步骤3：配置环境变量

**Windows PowerShell**：
```powershell
$env:MCP_SERVER_COMMAND="npx @modelcontextprotocol/server-filesystem"
```

**Linux/Mac**：
```bash
export MCP_SERVER_COMMAND="npx @modelcontextprotocol/server-filesystem"
```

#### 步骤4：验证安装

```bash
python examples/test_mcp.py
```

### 方法3：从GitHub克隆

适合需要自定义或使用最新版本的开发者。

#### 步骤1：克隆官方仓库

```bash
git clone https://github.com/modelcontextprotocol/servers.git
cd servers
```

#### 步骤2：安装依赖

根据服务器类型，安装相应的依赖：

**Python服务器**：
```bash
cd python
pip install -r requirements.txt
```

**TypeScript/Node.js服务器**：
```bash
cd typescript
npm install
```

#### 步骤3：配置环境变量

**Python服务器示例**：
```powershell
# Windows PowerShell
$env:MCP_SERVER_COMMAND="python path/to/servers/python/filesystem/main.py"
```

```bash
# Linux/Mac
export MCP_SERVER_COMMAND="python path/to/servers/python/filesystem/main.py"
```

**TypeScript服务器示例**：
```powershell
# Windows PowerShell
$env:MCP_SERVER_COMMAND="node path/to/servers/typescript/filesystem/dist/index.js"
```

```bash
# Linux/Mac
export MCP_SERVER_COMMAND="node path/to/servers/typescript/filesystem/dist/index.js"
```

## 常见MCP服务器列表

### 文件系统服务器（Filesystem）

提供文件读写、目录列表等功能。

- **Python**: `python -m mcp.server.filesystem`
- **npm**: `npx @modelcontextprotocol/server-filesystem`

### GitHub服务器

提供GitHub API访问功能。

- **npm**: `npx @modelcontextprotocol/server-github`
- 需要配置GitHub token

### SQLite服务器

提供SQLite数据库操作功能。

- **npm**: `npx @modelcontextprotocol/server-sqlite`

### Puppeteer服务器（浏览器控制）

提供浏览器自动化功能，可以替代 Playwright 控制浏览器。

- **npm**: `npx -y @modelcontextprotocol/server-puppeteer`
- 需要 Node.js 和 npm
- 支持浏览器导航、点击、输入、截图等操作

**配置示例：**
```bash
# Windows PowerShell
$env:MCP_PUPPETEER_COMMAND="npx -y @modelcontextprotocol/server-puppeteer"

# Linux/Mac
export MCP_PUPPETEER_COMMAND="npx -y @modelcontextprotocol/server-puppeteer"
```

**注意：** 如果配置了 Puppeteer MCP 服务器，Agent 会自动检测并使用它来控制浏览器，而不是使用 Playwright。如果 Puppeteer MCP 不可用，会自动回退到 Playwright。

### 其他服务器

更多MCP服务器可以在以下位置找到：
- [官方服务器仓库](https://github.com/modelcontextprotocol/servers)
- [MCP服务器列表](https://modelcontextprotocol.io/servers)

## 在项目中使用

### 方式1：通过环境变量

设置环境变量后，Agent会自动使用MCP服务器：

```python
from src.main import create_agent
from src.core.types import AgentConfig

config = AgentConfig(
    mcp_enabled=True,
    mcp_server_command=None,  # 从环境变量读取
    mcp_transport="stdio",
    use_mcp_browser=True,  # 启用 MCP 浏览器控制（可选）
    mcp_puppeteer_command=None  # 从环境变量读取
)

agent = create_agent(config)
```

### 方式2：直接在代码中指定

```python
from src.main import create_agent
from src.core.types import AgentConfig

config = AgentConfig(
    mcp_enabled=True,
    mcp_server_command="python -m mcp.server.filesystem",
    mcp_transport="stdio",
    use_mcp_browser=True,  # 启用 MCP 浏览器控制
    mcp_puppeteer_command="npx -y @modelcontextprotocol/server-puppeteer"
)

agent = create_agent(config)
```

### 使用 MCP Puppeteer 控制浏览器

如果配置了 Puppeteer MCP 服务器，Agent 会自动检测并使用它来控制浏览器，而不是使用 Playwright。这样可以：

1. **使用本地浏览器**：通过 MCP Puppeteer 控制本地已安装的浏览器
2. **无需安装 Playwright**：如果只使用 MCP Puppeteer，可以不需要 Playwright
3. **更好的集成**：通过 MCP 协议统一管理所有工具

**配置步骤：**

1. 安装 Puppeteer MCP 服务器（需要 Node.js）：
   ```bash
   npm install -g @modelcontextprotocol/server-puppeteer
   ```

2. 设置环境变量：
   ```bash
   # Windows PowerShell
   $env:MCP_ENABLED="true"
   $env:MCP_PUPPETEER_COMMAND="npx -y @modelcontextprotocol/server-puppeteer"
   
   # Linux/Mac
   export MCP_ENABLED="true"
   export MCP_PUPPETEER_COMMAND="npx -y @modelcontextprotocol/server-puppeteer"
   ```

3. Agent 会自动检测并使用 Puppeteer MCP 工具控制浏览器

**注意：** 如果 Puppeteer MCP 不可用或连接失败，Agent 会自动回退到 Playwright，确保功能正常。

## 故障排除

### 问题1：找不到MCP服务器模块

**解决方案**：
- 确保已正确安装MCP包：`pip list | grep mcp` 或 `npm list -g | grep mcp`
- 检查Python路径或Node.js路径是否正确
- 尝试使用完整路径

### 问题2：连接失败

**解决方案**：
- 检查MCP服务器命令是否正确
- 查看控制台错误信息
- 确保MCP服务器支持stdio传输方式

### 问题3：工具未发现

**解决方案**：
- 确保MCP服务器正确启动
- 检查MCP服务器是否实现了`tools/list`方法
- 查看日志输出

### 问题4：权限错误

**解决方案**：
- 确保有足够的权限访问文件系统
- 检查环境变量设置是否正确
- 对于npm全局安装，可能需要使用`sudo`（Linux/Mac）

## 推荐配置

对于大多数用户，推荐使用**方法1（Python MCP包）**：

```bash
# 1. 安装
pip install mcp

# 2. 设置环境变量（Windows PowerShell）
$env:MCP_SERVER_COMMAND="python -m mcp.server.filesystem"

# 3. 运行测试
python examples/test_mcp.py
```

## 更多资源

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP GitHub仓库](https://github.com/modelcontextprotocol)
- [MCP服务器列表](https://modelcontextprotocol.io/servers)


# MCP 服务器快速开始指南

本指南帮助您快速配置和使用真实的 MCP 服务器来测试获取本地浏览器应用。

## 方法 1：使用快速配置脚本（推荐）

### Windows PowerShell

```powershell
# 运行配置脚本
.\examples\setup_mcp.ps1
```

脚本会自动：
- 检测 Node.js 和 Python 是否安装
- 提供多种 MCP 服务器选项
- 自动设置环境变量
- 安装必要的依赖（如果需要）

## 方法 2：手动配置

### 选项 A：Puppeteer MCP 服务器（推荐，支持浏览器控制）

**前提条件：** 需要安装 Node.js

1. **安装 Puppeteer MCP 服务器：**
   ```powershell
   npm install -g @modelcontextprotocol/server-puppeteer
   ```

2. **设置环境变量：**
   ```powershell
   $env:MCP_ENABLED = "true"
   $env:MCP_SERVER_COMMAND = "npx -y @modelcontextprotocol/server-puppeteer"
   ```

3. **永久设置（可选）：**
   ```powershell
   [System.Environment]::SetEnvironmentVariable('MCP_ENABLED', 'true', 'User')
   [System.Environment]::SetEnvironmentVariable('MCP_SERVER_COMMAND', 'npx -y @modelcontextprotocol/server-puppeteer', 'User')
   ```

### 选项 B：Filesystem MCP 服务器（文件系统操作）

**前提条件：** 需要安装 Python

1. **安装 MCP 包：**
   ```powershell
   pip install mcp
   ```

2. **设置环境变量：**
   ```powershell
   $env:MCP_ENABLED = "true"
   $env:MCP_SERVER_COMMAND = "python -m mcp.server.filesystem"
   ```

3. **永久设置（可选）：**
   ```powershell
   [System.Environment]::SetEnvironmentVariable('MCP_ENABLED', 'true', 'User')
   [System.Environment]::SetEnvironmentVariable('MCP_SERVER_COMMAND', 'python -m mcp.server.filesystem', 'User')
   ```

## 测试配置

配置完成后，运行测试脚本：

```powershell
python examples/test_browser_apps.py
```

测试脚本会：
1. 连接到 MCP 服务器
2. 列出所有可用工具
3. 查找与浏览器/应用程序相关的工具
4. 尝试获取本地浏览器应用列表

## 常见问题

### Q1: 连接失败怎么办？

**可能的原因：**
- MCP 服务器命令不正确
- MCP 服务器未安装或不可用
- Node.js 或 Python 未正确安装

**解决方案：**
1. 检查环境变量是否正确设置：`echo $env:MCP_SERVER_COMMAND`
2. 手动测试 MCP 服务器命令是否能运行
3. 查看错误日志获取详细信息

### Q2: 找不到浏览器应用相关的工具？

**可能的原因：**
- 当前 MCP 服务器不支持应用程序列表功能
- 需要使用支持浏览器控制的 MCP 服务器（如 Puppeteer）

**解决方案：**
- 使用 Puppeteer MCP 服务器：`$env:MCP_SERVER_COMMAND='npx -y @modelcontextprotocol/server-puppeteer'`
- 查看 MCP 服务器的文档，了解支持的功能

### Q3: 环境变量设置后仍然无效？

**可能的原因：**
- 环境变量只在当前 PowerShell 会话中有效
- 需要重新打开 PowerShell 窗口（如果设置了永久环境变量）

**解决方案：**
- 在当前 PowerShell 会话中直接设置：`$env:MCP_SERVER_COMMAND='...'`
- 或者设置永久环境变量后，重新打开 PowerShell 窗口

## 更多信息

- 详细配置说明：`docs/MCP_SETUP.md`
- MCP 官方文档：https://modelcontextprotocol.io/
- MCP 服务器列表：https://modelcontextprotocol.io/servers


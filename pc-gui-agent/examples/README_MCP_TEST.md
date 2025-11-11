# MCP功能测试说明

本文档说明如何测试MCP（Model Context Protocol）功能。

## 测试文件

1. **`test_mcp.py`** - MCP功能测试示例
   - 测试MCP客户端连接
   - 测试MCP工具集成
   - 测试Agent使用MCP工具

2. **`mock_mcp_server.py`** - 简单的MCP服务器模拟器
   - 模拟MCP服务器响应
   - 提供基本的文件读写工具（read_file, write_file, list_directory）

## 快速开始

### 方法1：使用模拟MCP服务器（推荐用于测试）

1. **设置环境变量**（Windows PowerShell）：
   ```powershell
   $env:MCP_SERVER_COMMAND="python examples/mock_mcp_server.py"
   ```

   或（Linux/Mac）：
   ```bash
   export MCP_SERVER_COMMAND="python examples/mock_mcp_server.py"
   ```

2. **运行测试**：
   ```bash
   python examples/test_mcp.py
   ```

### 方法2：使用真实的MCP服务器

#### 安装真实MCP服务器

有三种方式安装真实的MCP服务器：

**方法A：使用Python MCP包（推荐）**

1. 安装MCP Python包：
   ```bash
   pip install mcp
   ```

2. 设置环境变量（Windows PowerShell）：
   ```powershell
   $env:MCP_SERVER_COMMAND="python -m mcp.server.filesystem"
   ```

3. 或（Linux/Mac）：
   ```bash
   export MCP_SERVER_COMMAND="python -m mcp.server.filesystem"
   ```

**方法B：使用npm包**

1. 安装Node.js和npm（如果还没有）

2. 安装MCP服务器包：
   ```bash
   npm install -g @modelcontextprotocol/server-filesystem
   ```

3. 设置环境变量（Windows PowerShell）：
   ```powershell
   $env:MCP_SERVER_COMMAND="npx @modelcontextprotocol/server-filesystem"
   ```

4. 或（Linux/Mac）：
   ```bash
   export MCP_SERVER_COMMAND="npx @modelcontextprotocol/server-filesystem"
   ```

**方法C：从GitHub克隆**

1. 克隆官方仓库：
   ```bash
   git clone https://github.com/modelcontextprotocol/servers.git
   cd servers
   ```

2. 安装依赖并运行（根据具体服务器类型）

#### 运行测试

设置环境变量后，运行测试：
```bash
python examples/test_mcp.py
```

> 详细安装说明请参考 `docs/MCP_SETUP.md`

## 测试内容

### 1. MCP客户端测试
- 连接到MCP服务器
- 发现可用工具
- 测试调用工具（如read_file）

### 2. MCP工具集成测试
- 创建MCP工具包装器
- 注册到工具注册表
- 测试执行MCP工具

### 3. Agent使用MCP测试
- 初始化Agent（自动连接MCP）
- 查看注册的工具
- 验证MCP工具已正确集成

## 在GUI应用中使用MCP

1. **设置环境变量**（同上）

2. **运行GUI应用**：
   ```bash
   python gui_main.py
   ```

3. **在GUI中输入任务**，Agent会自动使用MCP工具。例如：
   - "读取README.md文件"
   - "列出当前目录的文件"
   - "写入一个测试文件"

## 在代码中使用MCP

```python
import asyncio
from src.main import create_agent
from src.core.types import AgentConfig

async def main():
    # 创建配置
    config = AgentConfig(
        mcp_enabled=True,
        mcp_server_command="python examples/mock_mcp_server.py",
        mcp_transport="stdio"
    )
    
    # 创建Agent
    agent = create_agent(config)
    
    try:
        # 初始化（会自动连接MCP并注册工具）
        await agent.initialize()
        
        # 执行任务（Agent会自动使用MCP工具）
        result = await agent.execute_task("读取README.md文件")
        print(result)
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 模拟MCP服务器提供的工具

`mock_mcp_server.py` 提供以下工具：

1. **read_file** - 读取文件内容
   - 参数：`path` (string) - 文件路径

2. **write_file** - 写入文件内容
   - 参数：`path` (string) - 文件路径
   - 参数：`content` (string) - 文件内容

3. **list_directory** - 列出目录内容
   - 参数：`path` (string) - 目录路径

## 故障排除

### 问题1：连接失败
- 确保MCP服务器命令正确
- 检查Python环境是否包含所需的MCP服务器包
- 查看控制台错误信息

### 问题2：工具未发现
- 确保MCP服务器正确启动
- 检查MCP服务器是否实现了`tools/list`方法
- 查看日志输出

### 问题3：工具执行失败
- 检查工具参数是否正确
- 确保文件路径存在（对于文件操作工具）
- 查看错误消息

## 注意事项

1. **环境变量**：确保在运行测试前设置`MCP_SERVER_COMMAND`环境变量

2. **Python版本**：确保使用Python 3.8+

3. **异步执行**：所有MCP操作都是异步的，需要使用`asyncio.run()`或`await`

4. **资源清理**：测试完成后，确保调用`disconnect()`或`close()`方法清理资源


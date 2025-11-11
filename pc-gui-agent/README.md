# PC GUI Agent框架

面向PC（个人电脑）的GUI Agent框架，支持GUI操作、代码生成和工具调用。

## 功能特性

- 🤖 **智能规划**：使用开源LLM进行任务分解和规划
- 🛠️ **混合动作空间**：支持GUI操作、代码生成、MCP工具调用
- 🔄 **反思机制**：自动评估执行结果并调整策略
- 💾 **记忆系统**：存储历史任务经验和工具使用记录
- 🎯 **模块化设计**：Planner、Worker、Reflector、Memory等核心模块

## 技术栈

- **语言**：Python 3.8+
- **LLM**：Ollama（本地部署）
- **GUI操作**：Playwright
- **数据库**：SQLite（aiosqlite）
- **类型验证**：Pydantic

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装Playwright浏览器

```bash
playwright install
```

### 3. 配置环境变量

复制`.env.example`为`.env`并修改配置：

```bash
cp .env.example .env
```

编辑`.env`文件，设置Ollama的URL和模型名称。

### 4. 确保Ollama服务运行

确保本地Ollama服务正在运行，并且已下载所需模型：

```bash
ollama pull llama3.1:latest
```

## 快速开始

```python
from src.main import create_agent

# 创建Agent实例
agent = create_agent()

# 执行任务
result = await agent.execute_task("在浏览器中打开百度并搜索'Python'")
```

## 项目结构

```
pc-gui-agent/
├── src/
│   ├── core/          # 核心模块（Orchestrator、Planner、Worker等）
│   ├── llm/           # LLM客户端和Prompt模板
│   ├── tools/         # 工具系统
│   └── utils/         # 工具函数
├── examples/          # 使用示例
├── tests/             # 测试文件
└── data/              # 数据存储（SQLite数据库）
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 类型检查

```bash
mypy src/
```

## 许可证

MIT


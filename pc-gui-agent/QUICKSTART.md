# 快速开始指南

## 前置要求

1. **Python 3.8+**
2. **Ollama已安装并运行**
3. **已下载模型**（如llama3.1:latest）

## 安装步骤

### 1. 安装依赖

```bash
cd competition/pc-gui-agent
pip install -r requirements.txt
```

### 2. 安装Playwright浏览器

```bash
playwright install
```

### 3. 配置环境变量

复制环境变量示例文件：

```bash
# Windows
copy env.example .env

# Linux/Mac
cp env.example .env
```

编辑`.env`文件，确保Ollama配置正确。

### 4. 确保Ollama运行

```bash
# 检查Ollama是否运行
ollama list

# 如果没有模型，下载模型
ollama pull llama3.1:latest
```

## 运行示例

```bash
python examples/basic_usage.py
```

## 使用方式

```python
import asyncio
from src.main import create_agent

async def main():
    # 创建Agent
    agent = create_agent()
    await agent.initialize()
    
    # 执行任务
    result = await agent.execute_task("在浏览器中打开百度")
    
    print(result)
    
    # 关闭Agent
    await agent.close()

asyncio.run(main())
```

## 常见问题

1. **Ollama连接失败**
   - 确保Ollama服务正在运行：`ollama serve`
   - 检查`.env`中的`OLLAMA_BASE_URL`配置

2. **模型不存在**
   - 使用`ollama pull llama3.1:latest`下载模型
   - 或修改`.env`中的`OLLAMA_MODEL`为已安装的模型

3. **Playwright浏览器问题**
   - 运行`playwright install`安装浏览器
   - 确保有足够的系统权限


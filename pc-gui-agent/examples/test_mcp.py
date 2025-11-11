"""
MCP功能测试示例
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.client import MCPClient
from src.tools.mcp_tool import create_mcp_tools
from src.tools.registry import ToolRegistry
from src.core.types import AgentConfig
from src.main import create_agent


async def test_mcp_client():
    """测试MCP客户端连接和工具发现"""
    print("=== 测试MCP客户端 ===\n")
    
    # 创建MCP客户端（需要配置MCP服务器命令）
    mcp_command = os.getenv("MCP_SERVER_COMMAND")
    if not mcp_command:
        print("⚠️  未设置MCP_SERVER_COMMAND环境变量")
        print()
        print("   安装真实MCP服务器的方法：")
        print()
        print("   方法1：使用Python MCP包（推荐）")
        print("   - pip install mcp")
        print("   - Windows: $env:MCP_SERVER_COMMAND='python -m mcp.server.filesystem'")
        print("   - Linux/Mac: export MCP_SERVER_COMMAND='python -m mcp.server.filesystem'")
        print()
        print("   方法2：使用npm包")
        print("   - npm install -g @modelcontextprotocol/server-filesystem")
        print("   - Windows: $env:MCP_SERVER_COMMAND='npx @modelcontextprotocol/server-filesystem'")
        print("   - Linux/Mac: export MCP_SERVER_COMMAND='npx @modelcontextprotocol/server-filesystem'")
        print()
        print("   方法3：使用模拟服务器（仅用于测试）")
        print("   - Windows: $env:MCP_SERVER_COMMAND='python examples/mock_mcp_server.py'")
        print("   - Linux/Mac: export MCP_SERVER_COMMAND='python examples/mock_mcp_server.py'")
        print()
        print("   详细说明请参考: docs/MCP_SETUP.md")
        print()
        return False
    
    client = MCPClient(
        server_command=mcp_command,
        transport="stdio"
    )
    
    try:
        # 连接MCP服务器
        print("1. 连接到MCP服务器...")
        connected = await client.connect()
        
        if not connected:
            print("❌ 连接失败")
            return False
        
        print("✅ 连接成功\n")
        
        # 列出可用工具
        print("2. 发现可用工具...")
        tools = await client.list_tools()
        print(f"   发现 {len(tools)} 个工具：")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')}")
        print()
        
        # 测试调用工具（如果有read_file工具）
        if any(t.get('name') == 'read_file' for t in tools):
            print("3. 测试调用read_file工具...")
            result = await client.call_tool(
                name="read_file",
                arguments={"path": str(Path(__file__).parent.parent / "README.md")}
            )
            # 处理新的返回格式（官方 SDK）
            if result:
                if result.get("isError"):
                    print(f"   ❌ 错误: {result.get('error', 'Unknown error')}")
                elif "text" in result:
                    # 使用提取的 text 字段
                    text = result["text"][:100]
                    print(f"   结果: {text}...")
                elif "content" in result:
                    # 使用 content 数组
                    content = result["content"]
                    if content and len(content) > 0:
                        first_item = content[0]
                        if isinstance(first_item, dict):
                            text = first_item.get("text", "")[:100]
                            print(f"   结果: {text}...")
                        else:
                            print(f"   结果: {content}")
                    else:
                        print(f"   结果: {result}")
                elif "structuredContent" in result:
                    print(f"   结构化结果: {result['structuredContent']}")
                else:
                    print(f"   结果: {result}")
            else:
                print(f"   结果: {result}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()


async def test_mcp_tool_integration():
    """测试MCP工具集成到工具系统"""
    print("\n=== 测试MCP工具集成 ===\n")
    
    mcp_command = os.getenv("MCP_SERVER_COMMAND")
    if not mcp_command:
        print("⚠️  未设置MCP_SERVER_COMMAND环境变量，跳过测试")
        return False
    
    # 创建MCP客户端
    client = MCPClient(
        server_command=mcp_command,
        transport="stdio"
    )
    
    try:
        # 连接
        await client.connect()
        
        # 创建工具包装器
        print("1. 创建MCP工具包装器...")
        mcp_tools = create_mcp_tools(client)
        print(f"   创建了 {len(mcp_tools)} 个工具包装器\n")
        
        if len(mcp_tools) == 0:
            print("⚠️  没有发现MCP工具，跳过后续测试")
            return False
        
        # 注册到工具注册表
        print("2. 注册到工具注册表...")
        registry = ToolRegistry()
        registry.register_multiple(mcp_tools)
        
        # 列出所有工具
        print("3. 工具注册表中的工具：")
        tools_list = registry.get_tools_list()
        for tool in tools_list:
            print(f"   - {tool['name']}: {tool['description']}")
        print()
        
        # 测试执行工具
        mcp_tool_names = [t['name'] for t in tools_list if t['name'].startswith('mcp_')]
        if mcp_tool_names:
            test_tool_name = mcp_tool_names[0]
            print(f"4. 测试执行MCP工具 '{test_tool_name}'...")
            
            # 根据工具名称确定参数
            test_args = None
            if 'read_file' in test_tool_name or 'readFile' in test_tool_name:
                test_file = Path(__file__).parent.parent / "README.md"
                if test_file.exists():
                    test_args = {"path": str(test_file)}
                else:
                    print(f"   ⚠️  测试文件不存在: {test_file}")
                    print(f"   跳过执行测试")
                    return True
            elif 'write_file' in test_tool_name or 'writeFile' in test_tool_name:
                test_file = Path(__file__).parent / "test_output.txt"
                test_args = {
                    "path": str(test_file),
                    "content": "这是测试写入的内容"
                }
            elif 'list_directory' in test_tool_name or 'listDirectory' in test_tool_name:
                test_dir = str(Path(__file__).parent.parent)
                test_args = {"path": test_dir}
            elif 'navigate' in test_tool_name:
                # Puppeteer navigate 工具
                test_args = {"url": "https://www.example.com"}
            else:
                print(f"   ⚠️  未知工具类型: {test_tool_name}")
                print(f"   跳过执行测试")
                return True
            
            if test_args:
                result = await registry.execute(test_tool_name, test_args)
                print(f"   执行结果: {result.get('success')}")
                if result.get('success'):
                    data = result.get('data', '')
                    if isinstance(data, str) and len(data) > 100:
                        print(f"   数据预览: {data[:100]}...")
                        print(f"   数据长度: {len(data)} 字符")
                    else:
                        print(f"   数据: {data}")
                else:
                    print(f"   错误: {result.get('error')}")
                    print(f"   消息: {result.get('message')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()


async def test_agent_with_mcp():
    """测试Agent使用MCP工具"""
    print("\n=== 测试Agent使用MCP工具 ===\n")
    
    # 创建配置
    config = AgentConfig(
        mcp_enabled=True,
        mcp_server_command=os.getenv("MCP_SERVER_COMMAND"),
        mcp_transport="stdio"
    )
    
    if not config.mcp_server_command:
        print("⚠️  未设置MCP_SERVER_COMMAND，跳过测试")
        return False
    
    # 创建Agent
    agent = create_agent(config)
    
    try:
        # 初始化（会自动连接MCP并注册工具）
        print("1. 初始化Agent（会自动连接MCP）...")
        await agent.initialize()
        print("✅ 初始化完成\n")
        
        # 查看注册的工具
        print("2. 已注册的工具：")
        tools_list = agent.tool_registry.get_tools_list()
        # 过滤 MCP 工具（名称以 mcp_ 开头）
        mcp_tools = [t for t in tools_list if t['name'].startswith('mcp_')]
        gui_tools = [t for t in tools_list if not t['name'].startswith('mcp_')]
        
        print(f"   GUI工具数量: {len(gui_tools)}")
        print(f"   MCP工具数量: {len(mcp_tools)}")
        print()
        
        if mcp_tools:
            print("   MCP工具列表（前10个）：")
            for tool in mcp_tools[:10]:
                # 显示工具名称和描述的前50个字符
                desc_preview = tool['description'][:50] + "..." if len(tool['description']) > 50 else tool['description']
                print(f"   - {tool['name']}: {desc_preview}")
            if len(mcp_tools) > 10:
                print(f"   ... 还有 {len(mcp_tools) - 10} 个工具")
            print()
        else:
            print("   ⚠️  未发现 MCP 工具")
            print("   提示：检查 MCP_SERVER_COMMAND 环境变量是否正确设置")
            print()
        
        # 注意：这里不执行实际任务，因为需要Ollama运行
        print("3. Agent已准备好使用MCP工具")
        print("   可以通过以下方式测试：")
        print("   - 运行GUI应用: python gui_main.py")
        print("   - 或运行基础示例: python examples/basic_usage.py")
        print("   - 在任务中使用MCP工具（如：读取文件、写入文件等）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await agent.close()


async def main():
    """主测试函数"""
    print("=" * 60)
    print("MCP功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试1：MCP客户端
    result1 = await test_mcp_client()
    results.append(("MCP客户端测试", result1))
    
    # 测试2：MCP工具集成
    result2 = await test_mcp_tool_integration()
    results.append(("MCP工具集成测试", result2))
    
    # 测试3：Agent使用MCP
    result3 = await test_agent_with_mcp()
    results.append(("Agent使用MCP测试", result3))
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败/跳过"
        print(f"{name}: {status}")
    print("=" * 60)
    
    # 如果所有测试都通过，返回0，否则返回1
    all_passed = all(result for _, result in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


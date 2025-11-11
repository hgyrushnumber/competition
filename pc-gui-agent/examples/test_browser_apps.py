"""
测试 MCP 获取本地浏览器应用
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.client import MCPClient


async def find_browser_related_tools(tools):
    """
    查找与浏览器/应用程序相关的工具
    
    Args:
        tools: 工具列表
        
    Returns:
        相关的工具列表
    """
    browser_keywords = [
        "browser", "application", "app", "chrome", "firefox", "edge", 
        "safari", "list", "get", "installed", "launch", "open"
    ]
    
    related_tools = []
    for tool in tools:
        tool_name = tool.get('name', '').lower()
        tool_desc = tool.get('description', '').lower()
        
        # 检查工具名称或描述中是否包含浏览器相关关键词
        if any(keyword in tool_name or keyword in tool_desc for keyword in browser_keywords):
            related_tools.append(tool)
    
    return related_tools


def check_mcp_setup():
    """检查 MCP 配置"""
    mcp_command = os.getenv("MCP_SERVER_COMMAND")
    mcp_enabled = os.getenv("MCP_ENABLED", "false").lower() == "true"
    
    if not mcp_command:
        print("⚠️  未设置 MCP_SERVER_COMMAND 环境变量")
        print()
        print("   快速配置方法：")
        print()
        print("   方法 1：使用快速配置脚本（推荐）")
        print("   Windows PowerShell: .\\examples\\setup_mcp.ps1")
        print()
        print("   方法 2：手动设置环境变量")
        print("   Windows PowerShell:")
        print("   $env:MCP_ENABLED='true'")
        print("   $env:MCP_SERVER_COMMAND='npx -y @modelcontextprotocol/server-puppeteer'")
        print()
        print("   Linux/Mac:")
        print("   export MCP_ENABLED='true'")
        print("   export MCP_SERVER_COMMAND='npx -y @modelcontextprotocol/server-puppeteer'")
        print()
        print("   详细说明请参考: examples/QUICK_START_MCP.md")
        print()
        return False
    
    # 检查是否是模拟服务器
    if "mock_mcp_server" in mcp_command.lower():
        print("⚠️  检测到使用的是模拟 MCP 服务器")
        print("   模拟服务器不支持获取本地浏览器应用功能")
        print()
        print("   建议使用真实的 MCP 服务器：")
        print("   - Puppeteer MCP 服务器（推荐）：")
        print("     $env:MCP_SERVER_COMMAND='npx -y @modelcontextprotocol/server-puppeteer'")
        print("   - Filesystem MCP 服务器：")
        print("     $env:MCP_SERVER_COMMAND='python -m mcp.server.filesystem'")
        print()
        print("   详细说明请参考: examples/QUICK_START_MCP.md")
        print()
        return False
    
    return True


async def test_get_browser_apps():
    """测试获取本地浏览器应用列表"""
    print("=" * 60)
    print("测试 MCP 获取本地浏览器应用")
    print("=" * 60)
    print()
    
    # 检查 MCP 配置
    if not check_mcp_setup():
        return False
    
    # 获取 MCP 服务器命令
    mcp_command = os.getenv("MCP_SERVER_COMMAND")
    
    # 创建 MCP 客户端
    client = MCPClient(
        server_command=mcp_command,
        transport="stdio"
    )
    
    try:
        # 1. 连接到 MCP 服务器
        print("1. 连接到 MCP 服务器...")
        print(f"   服务器命令: {mcp_command}")
        connected = await client.connect()
        
        if not connected:
            print("❌ 连接失败")
            print()
            print("   可能的原因：")
            print("   - MCP 服务器命令不正确")
            print("   - MCP 服务器未安装或不可用")
            print("   - Node.js 或 Python 未正确安装")
            print()
            print("   解决方案：")
            print("   1. 检查环境变量：")
            print(f"      MCP_SERVER_COMMAND={mcp_command}")
            print()
            print("   2. 手动测试 MCP 服务器命令是否能运行")
            print()
            print("   3. 使用快速配置脚本重新配置：")
            print("      .\\examples\\setup_mcp.ps1")
            print()
            print("   4. 查看详细配置说明：")
            print("      examples/QUICK_START_MCP.md")
            print()
            return False
        
        print("✅ 连接成功\n")
        
        # 2. 列出所有可用工具
        print("2. 发现可用工具...")
        tools = await client.list_tools()
        print(f"   发现 {len(tools)} 个工具\n")
        
        if len(tools) == 0:
            print("⚠️  没有发现任何工具")
            return False
        
        # 显示所有工具
        print("   所有工具列表：")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.get('name')}: {tool.get('description', 'N/A')}")
        print()
        
        # 3. 查找与浏览器/应用程序相关的工具
        print("3. 查找与浏览器/应用程序相关的工具...")
        browser_tools = await find_browser_related_tools(tools)
        
        if not browser_tools:
            print("⚠️  没有找到与浏览器/应用程序相关的工具")
            print()
            print("   可能的原因：")
            print("   - 当前 MCP 服务器不支持应用程序列表功能")
            print("   - 需要使用支持浏览器控制的 MCP 服务器（如 Puppeteer）")
            print()
            print("   建议尝试：")
            print("   - 使用 Puppeteer MCP 服务器：")
            print("     $env:MCP_SERVER_COMMAND='npx -y @modelcontextprotocol/server-puppeteer'")
            print()
            return False
        
        print(f"   找到 {len(browser_tools)} 个相关工具：")
        for tool in browser_tools:
            print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')}")
        print()
        
        # 4. 尝试调用相关工具获取浏览器应用列表
        print("4. 尝试获取本地浏览器应用列表...")
        
        # 常见的工具名称模式
        possible_tool_names = [
            "list_applications",
            "get_browsers",
            "list_browsers",
            "get_installed_browsers",
            "list_installed_apps",
            "get_applications"
        ]
        
        success = False
        for tool in browser_tools:
            tool_name = tool.get('name')
            
            # 检查是否是列表应用程序的工具
            if any(pattern in tool_name.lower() for pattern in possible_tool_names):
                print(f"   尝试调用工具: {tool_name}")
                try:
                    # 尝试调用工具（可能需要不同的参数）
                    result = await client.call_tool(
                        name=tool_name,
                        arguments={}
                    )
                    
                    if result:
                        if result.get("isError"):
                            error = result.get('error', 'Unknown error')
                            print(f"   ❌ 错误: {error}")
                        else:
                            # 处理结果
                            print(f"   ✅ 调用成功")
                            print()
                            print("   结果:")
                            
                            # 尝试提取文本内容
                            if "text" in result:
                                print(result["text"])
                            elif "content" in result:
                                content = result["content"]
                                if isinstance(content, list) and len(content) > 0:
                                    for item in content:
                                        if isinstance(item, dict):
                                            if "text" in item:
                                                print(item["text"])
                                            else:
                                                print(item)
                                        else:
                                            print(item)
                                else:
                                    print(content)
                            elif "structuredContent" in result:
                                print(result["structuredContent"])
                            else:
                                print(result)
                            
                            success = True
                            break
                except Exception as e:
                    print(f"   ❌ 调用失败: {e}")
                    continue
        
        if not success:
            print("   ⚠️  未能成功获取浏览器应用列表")
            print()
            print("   可能的原因：")
            print("   - 工具需要特定的参数")
            print("   - 当前 MCP 服务器不支持此功能")
            print("   - 需要查看工具的输入模式（inputSchema）")
            print()
            print("   建议：")
            print("   - 查看工具的详细信息和参数要求")
            print("   - 尝试使用 Puppeteer MCP 服务器")
            print("   - 检查 MCP 服务器文档")
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()
        print()
        print("已断开 MCP 连接")


async def show_tool_details(client, tool_name):
    """显示工具的详细信息"""
    tools = await client.list_tools()
    for tool in tools:
        if tool.get('name') == tool_name:
            print(f"\n工具详细信息: {tool_name}")
            print(f"描述: {tool.get('description', 'N/A')}")
            if 'inputSchema' in tool:
                print(f"输入模式: {tool['inputSchema']}")
            return tool
    return None


async def main():
    """主函数"""
    print()
    success = await test_get_browser_apps()
    print()
    print("=" * 60)
    if success:
        print("✅ 测试完成")
    else:
        print("⚠️  测试未完全成功（可能是不支持的功能）")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


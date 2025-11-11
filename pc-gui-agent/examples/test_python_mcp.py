"""
Python MCP 服务器测试脚本

专门用于测试 Python MCP 服务器（examples/python_mcp_server.py）是否正常运行
"""
import asyncio
import sys
import os
import time
import importlib.util
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.client import MCPClient
from src.utils.logger import get_logger

# 设置日志级别为 DEBUG 以便查看详细日志
logger = get_logger(__name__)
logger.setLevel("DEBUG")


def check_python_mcp_package():
    """检查 Python MCP 包是否安装"""
    print("=" * 60)
    print("1. 检查 Python MCP 包安装")
    print("=" * 60)
    
    try:
        import mcp
        print("✅ MCP 包已安装")
        try:
            version = getattr(mcp, '__version__', '未知')
            print(f"   版本: {version}")
        except:
            pass
        return True
    except ImportError:
        print("❌ MCP 包未安装")
        print()
        print("   安装命令:")
        print("   pip install mcp")
        print()
        return False


def check_mcp_fastmcp_module():
    """检查是否可以导入 mcp.server.fastmcp"""
    print("=" * 60)
    print("2. 检查 mcp.server.fastmcp 模块")
    print("=" * 60)
    
    try:
        from mcp.server.fastmcp import FastMCP
        print("✅ mcp.server.fastmcp 模块可以导入")
        return True
    except ImportError as e:
        print(f"❌ 无法导入 mcp.server.fastmcp: {e}")
        print()
        print("   可能的原因:")
        print("   1. MCP 包未安装或版本过旧")
        print("   2. 需要安装额外的依赖")
        print()
        print("   尝试:")
        print("   pip install --upgrade mcp")
        print()
        return False


def check_python_mcp_server_file():
    """检查 Python MCP 服务器文件是否存在"""
    print("=" * 60)
    print("3. 检查 Python MCP 服务器文件")
    print("=" * 60)
    
    server_file = Path(__file__).parent / "python_mcp_server.py"
    if server_file.exists():
        print(f"✅ Python MCP 服务器文件存在: {server_file}")
        return True
    else:
        print(f"❌ Python MCP 服务器文件不存在: {server_file}")
        print()
        print("   请确保 examples/python_mcp_server.py 文件存在")
        print()
        return False


def check_module_exists(module_name: str) -> bool:
    """
    检测 Python 模块是否存在
    
    Args:
        module_name: 模块名称，如 "mcp.server.filesystem"
    
    Returns:
        如果模块存在返回 True，否则返回 False
    """
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError, AttributeError):
        return False


def check_environment_variables():
    """检查环境变量配置"""
    print("=" * 60)
    print("4. 检查环境变量配置")
    print("=" * 60)
    
    mcp_command = os.getenv("MCP_SERVER_COMMAND")
    
    if not mcp_command:
        print("⚠️  MCP_SERVER_COMMAND 环境变量未设置")
        print()
        print("   设置方法 (Windows PowerShell):")
        print("   $env:MCP_SERVER_COMMAND='python examples/python_mcp_server.py'")
        print()
        print("   设置方法 (Linux/Mac):")
        print("   export MCP_SERVER_COMMAND='python examples/python_mcp_server.py'")
        print()
        # 使用默认值：新创建的 Python MCP 服务器
        server_file = Path(__file__).parent / "python_mcp_server.py"
        if server_file.exists():
            # 使用 sys.executable 确保使用当前 Python 解释器（conda 环境）
            mcp_command = f"{sys.executable} {server_file}"
        else:
            mcp_command = f"{sys.executable} examples/python_mcp_server.py"
        print(f"   使用默认值: {mcp_command}")
    else:
        print(f"✅ MCP_SERVER_COMMAND: {mcp_command}")
        
        # 检测并替换 python 命令为 sys.executable（确保使用 conda 虚拟环境的 Python）
        original_command = mcp_command
        python_exe = sys.executable
        
        # 使用 shlex.split 来正确解析命令（处理引号等）
        import shlex
        try:
            parts = shlex.split(mcp_command)
            if parts and parts[0] in ("python", "python3"):
                # 替换第一个部分（python 或 python3）为 sys.executable
                parts[0] = python_exe
                mcp_command = " ".join(shlex.quote(str(part)) for part in parts)
                
                if mcp_command != original_command:
                    print(f"   ⚠️  检测到 'python' 命令，已自动替换为当前 Python 解释器")
                    print(f"   原始命令: {original_command}")
                    print(f"   修正命令: {mcp_command}")
                    print(f"   Python 解释器: {python_exe}")
                    print(f"   (这确保使用 conda 虚拟环境的 Python 而不是系统 Python)")
            
            # 检测是否是 -m 模块格式（如 python -m mcp.server.filesystem）
            if len(parts) >= 3 and parts[1] == "-m":
                module_name = parts[2]
                print(f"   检测到模块格式: -m {module_name}")
                
                # 检测模块是否存在
                if not check_module_exists(module_name):
                    print(f"   ❌ 模块 '{module_name}' 不存在")
                    print(f"   (MCP Python SDK 不提供预构建的服务器，只提供构建服务器的框架)")
                    print()
                    print(f"   ⚠️  自动回退到 python_mcp_server.py 服务器")
                    
                    # 使用我们创建的服务器
                    server_file = Path(__file__).parent / "python_mcp_server.py"
                    if server_file.exists():
                        mcp_command = f"{python_exe} {server_file}"
                        print(f"   回退命令: {mcp_command}")
                    else:
                        mcp_command = f"{python_exe} examples/python_mcp_server.py"
                        print(f"   回退命令: {mcp_command}")
                else:
                    print(f"   ✅ 模块 '{module_name}' 存在")
        except Exception:
            # 如果解析失败，尝试简单的字符串替换
            if mcp_command.strip().startswith("python ") or mcp_command.strip().startswith("python3 "):
                if mcp_command.strip().startswith("python "):
                    mcp_command = mcp_command.replace("python ", f"{python_exe} ", 1)
                elif mcp_command.strip().startswith("python3 "):
                    mcp_command = mcp_command.replace("python3 ", f"{python_exe} ", 1)
                
                if mcp_command != original_command:
                    print(f"   ⚠️  检测到 'python' 命令，已自动替换为当前 Python 解释器")
                    print(f"   原始命令: {original_command}")
                    print(f"   修正命令: {mcp_command}")
                    print(f"   Python 解释器: {python_exe}")
                    print(f"   (这确保使用 conda 虚拟环境的 Python 而不是系统 Python)")
    
    # 检查是否是 Python MCP 服务器
    if "python" in mcp_command.lower() and ("python_mcp_server.py" in mcp_command or "mcp.server" in mcp_command or sys.executable in mcp_command):
        print("✅ 配置为 Python MCP 服务器")
    else:
        print("⚠️  配置可能不是 Python MCP 服务器")
        print(f"   当前配置: {mcp_command}")
        print("   建议使用: python examples/python_mcp_server.py")
    
    return mcp_command


async def test_connection(mcp_command: str):
    """测试连接到 MCP 服务器"""
    print("=" * 60)
    print("5. 测试连接")
    print("=" * 60)
    
    print(f"   服务器命令: {mcp_command}")
    print("   开始连接...")
    
    client = MCPClient(
        server_command=mcp_command,
        transport="stdio"
    )
    
    start_time = time.time()
    
    try:
        connected = await client.connect()
        elapsed_time = time.time() - start_time
        
        if connected:
            print(f"✅ 连接成功 (耗时: {elapsed_time:.2f} 秒)")
            return client, True
        else:
            print(f"❌ 连接失败 (耗时: {elapsed_time:.2f} 秒)")
            return None, False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 连接异常 (耗时: {elapsed_time:.2f} 秒): {e}")
        import traceback
        traceback.print_exc()
        return None, False


async def test_list_tools(client: MCPClient):
    """测试获取工具列表"""
    print("=" * 60)
    print("6. 测试工具发现")
    print("=" * 60)
    
    if not client or not client.connected:
        print("❌ 客户端未连接，无法测试工具发现")
        return False
    
    try:
        start_time = time.time()
        tools = await client.list_tools()
        elapsed_time = time.time() - start_time
        
        if not tools:
            print("❌ 未发现任何工具")
            return False
        
        print(f"✅ 发现 {len(tools)} 个工具 (耗时: {elapsed_time:.2f} 秒)")
        print()
        print("   工具列表:")
        for idx, tool in enumerate(tools, 1):
            name = tool.get('name', 'N/A')
            description = tool.get('description', 'N/A')
            print(f"   {idx}. {name}")
            if description and description != 'N/A':
                desc_preview = description[:60] + "..." if len(description) > 60 else description
                print(f"      描述: {desc_preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取工具列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_call_tool(client: MCPClient, tool_name: str, arguments: dict):
    """测试调用工具"""
    print("=" * 60)
    print(f"7. 测试调用工具: {tool_name}")
    print("=" * 60)
    
    if not client or not client.connected:
        print("❌ 客户端未连接，无法测试工具调用")
        return False
    
    try:
        print(f"   工具名称: {tool_name}")
        print(f"   参数: {arguments}")
        print("   开始调用...")
        
        start_time = time.time()
        result = await client.call_tool(tool_name, arguments)
        elapsed_time = time.time() - start_time
        
        if result.get("isError"):
            error_msg = result.get("error", "Unknown error")
            print(f"❌ 工具调用返回错误 (耗时: {elapsed_time:.2f} 秒)")
            print(f"   错误信息: {error_msg}")
            return False
        
        print(f"✅ 工具调用成功 (耗时: {elapsed_time:.2f} 秒)")
        
        # 显示结果摘要
        if "text" in result:
            text = result["text"]
            preview = text[:100] + "..." if len(text) > 100 else text
            print(f"   结果预览: {preview}")
            print(f"   结果长度: {len(text)} 字符")
        elif "content" in result:
            content_count = len(result["content"])
            print(f"   内容项数量: {content_count}")
            if content_count > 0:
                first_item = result["content"][0]
                if isinstance(first_item, dict) and first_item.get("type") == "text":
                    text = first_item.get("text", "")
                    preview = text[:100] + "..." if len(text) > 100 else text
                    print(f"   第一个内容项预览: {preview}")
        else:
            print(f"   结果: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling(client: MCPClient):
    """测试错误处理"""
    print("=" * 60)
    print("8. 测试错误处理")
    print("=" * 60)
    
    if not client or not client.connected:
        print("❌ 客户端未连接，无法测试错误处理")
        return False
    
    # 测试1: 无效工具名称
    print("   测试1: 调用不存在的工具")
    try:
        result = await client.call_tool("nonexistent_tool", {})
        if result.get("isError"):
            print("   ✅ 正确返回错误")
        else:
            print("   ⚠️  未返回错误（可能工具存在）")
    except Exception as e:
        print(f"   ✅ 正确抛出异常: {type(e).__name__}")
    
    # 测试2: 无效参数
    print("   测试2: 使用无效参数调用工具")
    tools = client.get_tools()
    if tools:
        test_tool = tools[0]
        tool_name = test_tool.get("name")
        print(f"      使用工具: {tool_name}")
        try:
            result = await client.call_tool(tool_name, {"invalid_param": "invalid_value"})
            if result.get("isError"):
                print("   ✅ 正确返回错误")
            else:
                print("   ⚠️  未返回错误（可能参数被忽略）")
        except Exception as e:
            print(f"   ✅ 正确抛出异常: {type(e).__name__}")
    
    print("✅ 错误处理测试完成")
    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Python MCP 服务器测试")
    print("=" * 60)
    print()
    
    results = {}
    
    # 1. 检查 Python MCP 包
    results["MCP包"] = check_python_mcp_package()
    print()
    
    if not results["MCP包"]:
        print("❌ MCP 包未安装，无法继续测试")
        print()
        print("请先安装 MCP 包:")
        print("  pip install mcp")
        return 1
    
    # 2. 检查 mcp.server.fastmcp 模块
    results["FastMCP模块"] = check_mcp_fastmcp_module()
    print()
    
    if not results["FastMCP模块"]:
        print("❌ FastMCP 模块不可用，无法继续测试")
        return 1
    
    # 3. 检查 Python MCP 服务器文件
    results["服务器文件"] = check_python_mcp_server_file()
    print()
    
    if not results["服务器文件"]:
        print("❌ Python MCP 服务器文件不存在，无法继续测试")
        return 1
    
    # 4. 检查环境变量
    mcp_command = check_environment_variables()
    print()
    
    # 5. 测试连接
    client, connected = await test_connection(mcp_command)
    results["连接"] = connected
    print()
    
    if not connected:
        print("❌ 连接失败，无法继续测试")
        return 1
    
    # 6. 测试工具发现
    results["工具发现"] = await test_list_tools(client)
    print()
    
    if not results["工具发现"]:
        print("⚠️  未发现工具，跳过工具调用测试")
        await client.disconnect()
        return 0
    
    # 7. 测试工具调用
    tools = client.get_tools()
    tool_names = [t.get("name") for t in tools]
    
    # 测试 read_file 工具（如果可用）
    if "read_file" in tool_names:
        test_file = Path(__file__).parent.parent / "README.md"
        if test_file.exists():
            results["read_file工具"] = await test_call_tool(
                client,
                "read_file",
                {"path": str(test_file)}
            )
            print()
        else:
            print("⚠️  README.md 不存在，跳过 read_file 测试")
            results["read_file工具"] = None
    else:
        print("⚠️  read_file 工具不可用，跳过测试")
        results["read_file工具"] = None
    
    # 测试 list_directory 工具（如果可用）
    if "list_directory" in tool_names:
        test_dir = str(Path(__file__).parent.parent)
        results["list_directory工具"] = await test_call_tool(
            client,
            "list_directory",
            {"path": test_dir}
        )
        print()
    else:
        print("⚠️  list_directory 工具不可用，跳过测试")
        results["list_directory工具"] = None
    
    # 8. 测试错误处理
    results["错误处理"] = await test_error_handling(client)
    print()
    
    # 断开连接
    print("=" * 60)
    print("9. 断开连接")
    print("=" * 60)
    await client.disconnect()
    print("✅ 已断开连接")
    print()
    
    # 输出测试结果摘要
    print("=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    for name, result in results.items():
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⚠️  跳过"
        print(f"{name}: {status}")
    print("=" * 60)
    
    # 判断是否所有关键测试都通过
    critical_tests = ["MCP包", "FastMCP模块", "服务器文件", "连接", "工具发现"]
    all_critical_passed = all(results.get(test, False) for test in critical_tests)
    
    if all_critical_passed:
        print()
        print("✅ 所有关键测试通过！Python MCP 服务器运行正常。")
        return 0
    else:
        print()
        print("❌ 部分关键测试未通过，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


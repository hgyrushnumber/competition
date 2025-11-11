"""
检测MCP是否启用和使用
"""
import os
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def check_environment_variables():
    """检查环境变量"""
    print("=" * 60)
    print("1. 检查环境变量")
    print("=" * 60)
    
    mcp_enabled = os.getenv("MCP_ENABLED", "not set")
    mcp_server_command = os.getenv("MCP_SERVER_COMMAND", "not set")
    mcp_transport = os.getenv("MCP_TRANSPORT", "not set")
    
    print(f"MCP_ENABLED: {mcp_enabled}")
    print(f"MCP_SERVER_COMMAND: {mcp_server_command}")
    print(f"MCP_TRANSPORT: {mcp_transport}")
    print()
    
    # 判断是否启用
    is_enabled = mcp_enabled.lower() == "true"
    has_command = mcp_server_command != "not set" and mcp_server_command
    
    if is_enabled and has_command:
        print("[OK] MCP环境变量已正确设置")
        return True
    else:
        print("[X] MCP环境变量未设置或配置不完整")
        if not is_enabled:
            print("   - MCP_ENABLED 未设置为 'true'")
        if not has_command:
            print("   - MCP_SERVER_COMMAND 未设置")
        return False

def check_mcp_package():
    """检查MCP包是否安装"""
    print("=" * 60)
    print("2. 检查MCP包安装")
    print("=" * 60)
    
    try:
        import mcp
        print(f"[OK] MCP包已安装")
        try:
            print(f"   版本信息: {mcp.__version__ if hasattr(mcp, '__version__') else '未知'}")
        except:
            pass
        return True
    except ImportError:
        print("[X] MCP包未安装")
        print("   安装命令: pip install mcp")
        return False

def check_code_configuration():
    """检查代码配置"""
    print("=" * 60)
    print("3. 检查代码配置")
    print("=" * 60)
    
    try:
        from src.main import create_agent
        from src.core.types import AgentConfig
        
        # 创建测试配置
        config = AgentConfig(
            mcp_enabled=os.getenv("MCP_ENABLED", "false").lower() == "true",
            mcp_server_command=os.getenv("MCP_SERVER_COMMAND"),
            mcp_transport=os.getenv("MCP_TRANSPORT", "stdio")
        )
        
        print(f"mcp_enabled: {config.mcp_enabled}")
        print(f"mcp_server_command: {config.mcp_server_command}")
        print(f"mcp_transport: {config.mcp_transport}")
        print()
        
        if config.mcp_enabled and config.mcp_server_command:
            print("[OK] 代码配置正确，MCP将被启用")
            return True
        else:
            print("[X] 代码配置显示MCP未启用")
            return False
            
    except Exception as e:
        print(f"[X] 检查代码配置时出错: {e}")
        return False

async def check_mcp_connection():
    """检查MCP连接（如果已配置）"""
    print("=" * 60)
    print("4. 检查MCP连接")
    print("=" * 60)
    
    mcp_enabled = os.getenv("MCP_ENABLED", "false").lower() == "true"
    mcp_server_command = os.getenv("MCP_SERVER_COMMAND")
    
    if not mcp_enabled or not mcp_server_command:
        print("[!] MCP未启用，跳过连接测试")
        return None
    
    try:
        from src.mcp.client import MCPClient
        
        print(f"尝试连接到MCP服务器: {mcp_server_command}")
        client = MCPClient(
            server_command=mcp_server_command,
            transport=os.getenv("MCP_TRANSPORT", "stdio")
        )
        
        connected = await client.connect()
        if connected:
            print("[OK] MCP服务器连接成功")
            
            # 列出工具
            tools = await client.list_tools()
            print(f"   发现 {len(tools)} 个MCP工具:")
            for tool in tools[:5]:  # 只显示前5个
                print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')}")
            if len(tools) > 5:
                print(f"   ... 还有 {len(tools) - 5} 个工具")
            
            await client.disconnect()
            return True
        else:
            print("[X] MCP服务器连接失败")
            return False
            
    except Exception as e:
        print(f"[X] MCP连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("MCP使用情况检测")
    print("=" * 60 + "\n")
    
    results = {}
    
    # 1. 检查环境变量
    results["环境变量"] = check_environment_variables()
    print()
    
    # 2. 检查MCP包
    results["MCP包"] = check_mcp_package()
    print()
    
    # 3. 检查代码配置
    results["代码配置"] = check_code_configuration()
    print()
    
    # 4. 检查MCP连接（异步）
    import asyncio
    try:
        connection_result = asyncio.run(check_mcp_connection())
        results["MCP连接"] = connection_result
    except Exception as e:
        print(f"连接测试出错: {e}")
        results["MCP连接"] = None
    print()
    
    # 总结
    print("=" * 60)
    print("检测结果总结")
    print("=" * 60)
    
    for name, result in results.items():
        if result is True:
            status = "[OK] 通过"
        elif result is False:
            status = "[X] 失败"
        else:
            status = "[!] 跳过"
        print(f"{name}: {status}")
    
    print()
    
    # 给出建议
    if all(r for r in results.values() if r is not None):
        print("[OK] 所有检测通过！MCP已正确配置并可以使用。")
    else:
        print("[!] 部分检测未通过，请根据上述信息进行修复：")
        print()
        if not results.get("环境变量"):
            print("1. 设置环境变量：")
            print("   $env:MCP_ENABLED='true'")
            print("   $env:MCP_SERVER_COMMAND='python -m mcp.server.filesystem'")
            print()
        if not results.get("MCP包"):
            print("2. 安装MCP包：")
            print("   pip install mcp")
            print()

if __name__ == "__main__":
    main()


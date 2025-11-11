"""
基础使用示例
"""
import asyncio
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import create_agent


async def main():
    """主函数"""
    print("=== PC GUI Agent 基础使用示例 ===\n")
    
    # 创建Agent实例
    print("1. 创建Agent实例...")
    agent = create_agent()
    
    # 初始化Agent
    print("2. 初始化Agent...")
    await agent.initialize()
    
    # 执行任务示例
    print("\n3. 执行任务示例...")
    print("任务：在浏览器中打开百度并搜索'Python'")
    
    try:
        result = await agent.execute_task("在浏览器中打开百度并搜索'Python'")
        
        print(f"\n执行结果：")
        print(f"  任务ID: {result.get('task_id')}")
        print(f"  成功: {result.get('success')}")
        print(f"  消息: {result.get('message')}")
        
        if result.get('action_results'):
            print(f"\n动作执行结果：")
            for i, action_result in enumerate(result['action_results'], 1):
                # action_result 是 ActionResult 对象，不是字典
                print(f"  {i}. {action_result.message or 'N/A'}")
                if not action_result.success:
                    print(f"     错误: {action_result.error or 'N/A'}")
        
        if result.get('reflection'):
            reflection = result['reflection']
            print(f"\n反思结果：")
            print(f"  分析: {reflection.analysis[:100]}..." if len(reflection.analysis) > 100 else f"  分析: {reflection.analysis}")
            print(f"  需要重规划: {reflection.needs_replan}")
            print(f"  置信度: {reflection.confidence:.2f}")
    
    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭Agent
        print("\n4. 关闭Agent...")
        await agent.close()
        print("\n完成！")


if __name__ == "__main__":
    asyncio.run(main())


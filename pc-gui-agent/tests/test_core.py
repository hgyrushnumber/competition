"""
核心模块测试
"""
import pytest
import asyncio
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.types import Action, ActionType, TaskStatus
from tools.registry import ToolRegistry
from tools.gui_tools import NavigateTool, ClickTool


@pytest.fixture
def tool_registry():
    """工具注册表fixture"""
    registry = ToolRegistry()
    registry.register(NavigateTool())
    registry.register(ClickTool())
    return registry


@pytest.mark.asyncio
async def test_tool_registry(tool_registry):
    """测试工具注册表"""
    assert tool_registry.has("navigate")
    assert tool_registry.has("click")
    assert not tool_registry.has("nonexistent")
    
    tools_list = tool_registry.get_tools_list()
    assert len(tools_list) >= 2
    assert any(t["name"] == "navigate" for t in tools_list)


@pytest.mark.asyncio
async def test_action_creation():
    """测试Action创建"""
    action = Action(
        type=ActionType.GUI,
        tool="navigate",
        args={"url": "https://www.baidu.com"},
        description="打开百度"
    )
    
    assert action.type == ActionType.GUI
    assert action.tool == "navigate"
    assert action.args["url"] == "https://www.baidu.com"


def test_task_status_enum():
    """测试TaskStatus枚举"""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"


@pytest.mark.asyncio
async def test_tool_execution(tool_registry):
    """测试工具执行（需要Ollama和浏览器，可能跳过）"""
    # 这个测试需要实际环境，可以标记为skip
    pytest.skip("需要实际环境，跳过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


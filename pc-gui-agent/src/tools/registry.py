"""
工具注册表
"""
from typing import Dict, List, Optional, Any
from .base_tool import BaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting...")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def register_multiple(self, tools: List[BaseTool]) -> None:
        """
        批量注册工具
        
        Args:
            tools: 工具列表
        """
        for tool in tools:
            self.register(tool)
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例或None
        """
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            name: 工具名称
            
        Returns:
            是否存在
        """
        return name in self._tools
    
    def list_all(self) -> List[BaseTool]:
        """
        列出所有工具
        
        Returns:
            工具列表
        """
        return list(self._tools.values())
    
    def get_tools_list(self) -> List[Dict[str, str]]:
        """
        获取工具列表（用于LLM）
        
        Returns:
            工具信息列表，格式：[{"name": "...", "description": "..."}]
        """
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self._tools.values()
        ]
    
    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            name: 工具名称
            args: 工具参数
            
        Returns:
            执行结果
        """
        tool = self.get(name)
        if not tool:
            # 获取所有可用工具名称
            available_tools = list(self._tools.keys())
            available_tools_str = ", ".join(available_tools) if available_tools else "无"
            
            # 尝试找到相似的工具名称（简单匹配）
            similar_tools = [
                t for t in available_tools 
                if name.lower() in t.lower() or t.lower() in name.lower()
            ]
            
            error_msg = f"工具 '{name}' 不存在"
            suggestion_msg = ""
            
            if similar_tools:
                suggestion_msg = f" 您是否想使用: {', '.join(similar_tools)}?"
            elif available_tools:
                suggestion_msg = f" 可用工具: {available_tools_str}"
            
            return {
                "success": False,
                "error": f"Tool '{name}' not found",
                "message": error_msg + suggestion_msg,
                "available_tools": available_tools
            }
        
        try:
            # 验证参数
            if not tool.validate_args(args):
                return {
                    "success": False,
                    "error": "Invalid arguments",
                    "message": "参数验证失败"
                }
            
            # 执行工具
            result = await tool.execute(args)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"工具执行失败: {str(e)}"
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取工具统计信息
        
        Returns:
            统计信息
        """
        return {
            "total": len(self._tools),
            "tools": [tool.name for tool in self._tools.values()]
        }


# 全局工具注册表实例
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


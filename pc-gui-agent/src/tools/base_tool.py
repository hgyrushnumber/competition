"""
工具基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolArgs(BaseModel):
    """工具参数基类"""
    pass


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self):
        self.name = self.get_name()
        self.description = self.get_description()
    
    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            args: 工具参数
            
        Returns:
            执行结果，格式：{"success": bool, "data": Any, "error": str, "message": str}
        """
        pass
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """
        验证参数（可选实现）
        
        Args:
            args: 工具参数
            
        Returns:
            是否有效
        """
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具schema（用于LLM理解）
        
        Returns:
            Schema字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {}
        }


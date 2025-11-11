"""
MCP工具包装器
将MCP工具集成到现有的工具系统中
"""
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from ..mcp.client import MCPClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MCPTool(BaseTool):
    """MCP工具包装器"""
    
    def __init__(
        self,
        mcp_client: MCPClient,
        tool_name: str,
        tool_schema: Dict[str, Any]
    ):
        """
        初始化MCP工具包装器
        
        Args:
            mcp_client: MCP客户端实例
            tool_name: MCP工具名称
            tool_schema: MCP工具schema（包含描述、参数等）
        """
        # 先提取schema信息，再调用父类初始化（父类会调用get_name()和get_description()）
        self.mcp_client = mcp_client
        self.tool_name = tool_name
        self.tool_schema = tool_schema
        
        # 从schema中提取信息（必须在super().__init__()之前设置）
        self._name = tool_schema.get("name", tool_name)
        self._description = tool_schema.get("description", f"MCP tool: {tool_name}")
        self._input_schema = tool_schema.get("inputSchema", {})
        
        # 调用父类初始化（此时_name和_description已设置）
        super().__init__()
    
    def get_name(self) -> str:
        """获取工具名称（带 mcp_ 前缀）"""
        # 返回带 mcp_ 前缀的名称，以便识别 MCP 工具
        return f"mcp_{self._name}"
    
    def get_description(self) -> str:
        """获取工具描述"""
        return f"mcp_{self._name} - {self._description}"
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """
        验证参数
        
        Args:
            args: 工具参数
            
        Returns:
            是否有效
        """
        # 简单的参数验证
        # 可以根据inputSchema进行更详细的验证
        properties = self._input_schema.get("properties", {})
        required = self._input_schema.get("required", [])
        
        # 检查必需参数
        for param in required:
            if param not in args:
                logger.warning(f"Missing required parameter: {param}")
                return False
        
        # 检查参数类型（简单验证）
        for param_name, param_value in args.items():
            if param_name in properties:
                param_schema = properties[param_name]
                param_type = param_schema.get("type")
                
                if param_type == "string" and not isinstance(param_value, str):
                    logger.warning(f"Parameter {param_name} should be string")
                    return False
                elif param_type == "number" and not isinstance(param_value, (int, float)):
                    logger.warning(f"Parameter {param_name} should be number")
                    return False
                elif param_type == "boolean" and not isinstance(param_value, bool):
                    logger.warning(f"Parameter {param_name} should be boolean")
                    return False
        
        return True
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行MCP工具
        
        Args:
            args: 工具参数
            
        Returns:
            执行结果
        """
        try:
            # 通过MCP客户端调用工具
            result = await self.mcp_client.call_tool(
                name=self.tool_name,
                arguments=args
            )
            
            # 处理MCP工具返回结果（官方 SDK 返回格式）
            if isinstance(result, dict):
                # 检查是否有错误
                if result.get("isError", False):
                    error_msg = result.get("error", "Unknown error")
                    return {
                        "success": False,
                        "error": error_msg,
                        "message": f"MCP工具 {self.tool_name} 执行失败: {error_msg}"
                    }
                
                # 优先使用 text 字段（从 content 中提取的）
                if "text" in result:
                    return {
                        "success": True,
                        "data": result["text"],
                        "message": f"MCP工具 {self.tool_name} 执行成功"
                    }
                
                # 处理 content 数组
                content = result.get("content", [])
                if content and len(content) > 0:
                    # 提取第一个content项
                    first_content = content[0]
                    if isinstance(first_content, dict):
                        text = first_content.get("text", "")
                        if text:
                            return {
                                "success": True,
                                "data": text,
                                "message": f"MCP工具 {self.tool_name} 执行成功"
                            }
                
                # 处理结构化内容
                if "structuredContent" in result:
                    return {
                        "success": True,
                        "data": result["structuredContent"],
                        "message": f"MCP工具 {self.tool_name} 执行成功"
                    }
                
                # 如果没有特定格式，返回整个结果
                return {
                    "success": True,
                    "data": result,
                    "message": f"MCP工具 {self.tool_name} 执行成功"
                }
            else:
                return {
                    "success": True,
                    "data": result,
                    "message": f"MCP工具 {self.tool_name} 执行成功"
                }
        
        except Exception as e:
            logger.error(f"Error executing MCP tool '{self.tool_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"MCP工具 {self.tool_name} 执行失败: {str(e)}"
            }


def create_mcp_tools(mcp_client: MCPClient) -> List[MCPTool]:
    """
    从MCP客户端创建工具包装器列表
    
    Args:
        mcp_client: MCP客户端实例
        
    Returns:
        MCP工具包装器列表
    """
    tools = []
    mcp_tools = mcp_client.get_tools()
    
    for tool_schema in mcp_tools:
        tool_name = tool_schema.get("name")
        if tool_name:
            mcp_tool = MCPTool(
                mcp_client=mcp_client,
                tool_name=tool_name,
                tool_schema=tool_schema
            )
            tools.append(mcp_tool)
            logger.info(f"Created MCP tool wrapper: {tool_name}")
    
    return tools


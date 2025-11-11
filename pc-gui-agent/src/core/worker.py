"""
执行器模块
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from .types import Action, ActionResult, ActionType, Context
from .error_handler import ErrorHandler
from ..tools.registry import ToolRegistry, get_registry
from ..tools.element_finder import ElementFinder
from ..llm.ollama_client import OllamaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Worker:
    """执行器"""
    
    # 工具名称映射（常见中文名到实际工具名）
    TOOL_NAME_MAPPING = {
        "浏览器": "navigate",
        "导航": "navigate",
        "打开": "navigate",
        "点击": "click",
        "输入": "input",
        "滚动": "scroll",
        "截图": "screenshot",
        "等待": "wait",
    }
    
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        ollama_client: Optional[OllamaClient] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_exponential_backoff: bool = True
    ):
        """
        初始化执行器
        
        Args:
            tool_registry: 工具注册表（可选，默认使用全局注册表）
            ollama_client: Ollama客户端（用于元素查找，可选）
            max_retries: 最大重试次数
            retry_delay: 基础重试延迟（秒）
            use_exponential_backoff: 是否使用指数退避
        """
        self.tool_registry = tool_registry or get_registry()
        self.ollama_client = ollama_client
        self.element_finder = ElementFinder(ollama_client) if ollama_client else None
        self.error_handler = ErrorHandler()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_exponential_backoff = use_exponential_backoff
    
    def _normalize_tool_name(self, tool_name: str) -> str:
        """
        规范化工具名称（将常见中文名映射到实际工具名）
        
        Args:
            tool_name: 原始工具名称
            
        Returns:
            规范化后的工具名称
        """
        # 如果工具已存在，直接返回
        if self.tool_registry.has(tool_name):
            return tool_name
        
        # 尝试映射
        normalized = self.TOOL_NAME_MAPPING.get(tool_name)
        if normalized and self.tool_registry.has(normalized):
            logger.warning(
                f"Tool name '{tool_name}' not found, using mapped name '{normalized}'"
            )
            return normalized
        
        # 如果映射后仍不存在，返回原始名称（让工具注册表报错）
        return tool_name
    
    async def execute_action(
        self,
        action: Action,
        context: Optional[Context] = None
    ) -> ActionResult:
        """
        执行单个动作
        
        Args:
            action: 动作对象
            context: 执行上下文（可选）
            
        Returns:
            执行结果
        """
        start_time = time.time()
        action_id = f"{action.type}_{action.tool}_{int(start_time)}"
        
        logger.info(f"Executing action: {action.description} (tool: {action.tool})")
        
        try:
            # 根据动作类型执行
            if action.type == ActionType.GUI:
                result = await self._execute_gui_action(action, context)
            elif action.type == ActionType.CODE:
                result = await self._execute_code_action(action, context)
            elif action.type == ActionType.MCP:
                result = await self._execute_mcp_action(action, context)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action.type}",
                    "message": f"未知动作类型: {action.type}"
                }
            
            execution_time = time.time() - start_time
            
            return ActionResult(
                action_id=action_id,
                success=result.get("success", False),
                data=result.get("data"),
                error=result.get("error"),
                message=result.get("message", ""),
                execution_time=execution_time
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Action execution error: {e}")
            return ActionResult(
                action_id=action_id,
                success=False,
                error=str(e),
                message=f"动作执行异常: {str(e)}",
                execution_time=execution_time
            )
    
    async def _execute_gui_action(
        self,
        action: Action,
        context: Optional[Context]
    ) -> Dict[str, Any]:
        """
        执行GUI动作
        如果缺少target，自动分析DOM并补充
        """
        # 规范化工具名称
        normalized_tool = self._normalize_tool_name(action.tool)
        if normalized_tool != action.tool:
            action.tool = normalized_tool
        
        # 检查是否需要target参数的工具
        needs_target = action.tool in ['click', 'input']
        
        if needs_target and not action.args.get('target'):
            # 缺少target，尝试自动查找
            logger.info(f"Missing target for {action.tool}, attempting to find element...")
            
            if self.element_finder:
                try:
                    # 获取Page对象
                    from ..tools.gui_tools import GUITools
                    gui_tools = GUITools()
                    page = await gui_tools._get_page()
                    
                    # 根据工具类型确定元素类型
                    element_type = 'input' if action.tool == 'input' else 'button'
                    
                    # 查找元素
                    selector = await self.element_finder.find_element(
                        page=page,
                        action_description=action.description,
                        element_type=element_type
                    )
                    
                    if selector:
                        action.args['target'] = selector
                        logger.info(f"Auto-found target: {selector}")
                    else:
                        logger.warning(f"Could not find target for {action.description}")
                        return {
                            "success": False,
                            "error": "Could not find target element",
                            "message": f"无法找到目标元素: {action.description}"
                        }
                
                except Exception as e:
                    logger.error(f"Error in auto-finding element: {e}")
                    # 继续执行，让工具自己报错
            else:
                logger.warning("ElementFinder not available, cannot auto-find target")
        
        return await self.tool_registry.execute(action.tool, action.args)
    
    async def _execute_code_action(
        self,
        action: Action,
        context: Optional[Context]
    ) -> Dict[str, Any]:
        """执行代码动作（TODO: 后续实现）"""
        # 这里暂时返回未实现
        return {
            "success": False,
            "error": "Code execution not implemented yet",
            "message": "代码执行功能尚未实现"
        }
    
    async def _execute_mcp_action(
        self,
        action: Action,
        context: Optional[Context]
    ) -> Dict[str, Any]:
        """
        执行MCP工具动作
        
        Args:
            action: 动作对象
            context: 执行上下文
            
        Returns:
            执行结果
        """
        # MCP工具通过工具注册表执行
        # 工具名称格式：mcp_<tool_name>
        # 参数在action.args中
        return await self.tool_registry.execute(action.tool, action.args)
    
    async def execute_actions(
        self,
        actions: List[Action],
        context: Optional[Context] = None
    ) -> List[ActionResult]:
        """
        执行动作列表
        
        Args:
            actions: 动作列表
            context: 执行上下文（可选）
            
        Returns:
            执行结果列表
        """
        results = []
        
        for action in actions:
            # 检查依赖
            if action.dependencies:
                # 确保依赖的动作已成功执行
                dependency_ids = [r.action_id for r in results if r.success]
                if not all(dep in dependency_ids for dep in action.dependencies):
                    logger.warning(f"Action {action.tool} has unmet dependencies")
                    results.append(ActionResult(
                        action_id=f"{action.type}_{action.tool}",
                        success=False,
                        error="Unmet dependencies",
                        message="依赖的动作未成功执行"
                    ))
                    continue
            
            result = await self.execute_action(action, context)
            results.append(result)
            
            # 如果动作失败且是关键动作，可以中断执行
            if not result.success:
                logger.warning(f"Action failed: {result.message}")
        
        return results
    
    async def execute_with_retry(
        self,
        action: Action,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        context: Optional[Context] = None
    ) -> ActionResult:
        """
        带智能重试的执行（使用ErrorHandler进行错误分类和恢复策略）
        
        Args:
            action: 动作对象
            max_retries: 最大重试次数（可选，使用默认值）
            retry_delay: 基础重试延迟（秒，可选，使用默认值）
            context: 执行上下文（可选）
            
        Returns:
            执行结果
        """
        max_retries = max_retries or self.max_retries
        retry_delay = retry_delay or self.retry_delay
        
        last_result = None
        last_error = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                # 创建错误上下文
                if last_error:
                    error_context = self.error_handler.create_error_context(
                        error=last_error,
                        action_id=f"{action.type}_{action.tool}",
                        tool_name=action.tool,
                        args=action.args,
                        retry_count=attempt - 1
                    )
                    
                    # 获取恢复策略
                    recovery_action = self.error_handler.get_recovery_strategy(
                        error_context,
                        max_retries=max_retries,
                        retry_delay=retry_delay
                    )
                    
                    # 检查是否应该继续重试
                    if not recovery_action.should_retry:
                        logger.warning(
                            f"Recovery strategy suggests not retrying: {recovery_action.strategy.value}"
                        )
                        break
                    
                    # 计算重试延迟（支持指数退避）
                    actual_delay = self.error_handler.get_retry_delay(
                        error_context,
                        base_delay=retry_delay,
                        use_exponential_backoff=self.use_exponential_backoff
                    )
                    
                    logger.info(
                        f"Retrying action {action.tool} (attempt {attempt + 1}/{max_retries}) "
                        f"after {actual_delay:.2f}s delay. Strategy: {recovery_action.message}"
                    )
                    await asyncio.sleep(actual_delay)
                else:
                    # 如果没有错误信息，使用固定延迟
                    logger.info(f"Retrying action {action.tool} (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
            
            try:
                result = await self.execute_action(action, context)
                last_result = result
                last_error = None
                
                if result.success:
                    return result
                else:
                    # 如果执行失败，创建一个异常对象用于错误处理
                    error_msg = result.error or result.message or "Unknown error"
                    last_error = Exception(error_msg)
                    
            except Exception as e:
                last_error = e
                # 创建错误上下文
                error_context = self.error_handler.create_error_context(
                    error=e,
                    action_id=f"{action.type}_{action.tool}",
                    tool_name=action.tool,
                    args=action.args,
                    retry_count=attempt
                )
                
                # 获取恢复策略
                recovery_action = self.error_handler.get_recovery_strategy(
                    error_context,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                )
                
                # 创建失败结果
                last_result = ActionResult(
                    action_id=f"{action.type}_{action.tool}",
                    success=False,
                    error=str(e),
                    message=recovery_action.message
                )
                
                # 检查是否应该继续重试
                if not recovery_action.should_retry:
                    logger.warning(
                        f"Recovery strategy suggests not retrying: {recovery_action.strategy.value}"
                    )
                    break
        
        # 如果所有重试都失败，返回最后的结果
        if last_result:
            return last_result
        
        # 如果没有结果，返回默认失败结果
        return ActionResult(
            action_id=f"{action.type}_{action.tool}",
            success=False,
            error="Max retries exceeded",
            message="达到最大重试次数"
        )


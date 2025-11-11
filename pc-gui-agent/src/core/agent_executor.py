"""
Agent执行器模块
实现LLM实时指挥的逐步决策机制
"""
from typing import List, Dict, Any, Optional
from .types import (
    Action, ActionResult, StepDecision, Context, Task, TaskStatus
)
from .worker import Worker
from .planner import Planner
from .reflector import Reflector
from .error_handler import ErrorHandler
from ..llm.ollama_client import OllamaClient
from ..llm.prompt_templates import get_agent_step_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentExecutor:
    """Agent执行器 - LLM实时指挥模式"""
    
    def __init__(
        self,
        worker: Worker,
        planner: Planner,
        reflector: Reflector,
        ollama_client: OllamaClient,
        max_steps: int = 50
    ):
        """
        初始化Agent执行器
        
        Args:
            worker: 执行器实例
            planner: 规划器实例
            reflector: 反思器实例
            ollama_client: Ollama客户端
            max_steps: 最大执行步数
        """
        self.worker = worker
        self.planner = planner
        self.reflector = reflector
        self.ollama_client = ollama_client
        self.max_steps = max_steps
        self.error_handler = ErrorHandler()
    
    async def execute_task(
        self,
        goal: str,
        initial_context: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        执行任务（逐步决策模式）
        
        Args:
            goal: 用户目标
            initial_context: 初始上下文（可选）
            
        Returns:
            执行结果
        """
        logger.info(f"Starting agent-mode task execution: {goal}")
        
        # 创建任务对象
        from .types import Task
        import uuid
        from datetime import datetime
        
        task = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            goal=goal,
            subtasks=[],
            status=TaskStatus.RUNNING
        )
        
        # 创建上下文
        if initial_context is None:
            context = Context(task=task)
        else:
            context = initial_context
            context.task = task
        
        # 执行循环
        action_results: List[ActionResult] = []
        step_count = 0
        last_decision: Optional[StepDecision] = None
        
        try:
            while step_count < self.max_steps:
                step_count += 1
                logger.info(f"Step {step_count}/{self.max_steps}: Planning next action...")
                
                # 获取可用工具列表
                from ..tools.registry import get_registry
                tool_registry = get_registry()
                available_tools = tool_registry.get_tools_list()
                
                # 调用LLM决定下一步
                decision = await self._decide_next_step(
                    goal=goal,
                    context=context,
                    available_tools=available_tools,
                    last_decision=last_decision
                )
                
                # 检查是否应该继续
                if not decision.should_continue:
                    logger.info(f"Agent decided to stop at step {step_count}")
                    break
                
                # 检查是否应该重试上一步
                if decision.should_retry and action_results:
                    logger.info("Agent decided to retry last step")
                    if action_results:
                        last_result = action_results[-1]
                        # 重新执行上一步（简化处理，实际可以更复杂）
                        logger.info("Retrying last action...")
                        # 这里可以重新执行上一步的动作
                
                # 检查是否应该跳过
                if decision.should_skip:
                    logger.info("Agent decided to skip current step")
                    continue
                
                # 执行动作
                if decision.action:
                    logger.info(
                        f"Executing action: {decision.action.description} "
                        f"(tool: {decision.action.tool}, confidence: {decision.confidence:.2f})"
                    )
                    
                    result = await self.worker.execute_action(
                        action=decision.action,
                        context=context
                    )
                    
                    action_results.append(result)
                    context.action_results = action_results
                    
                    # 更新上下文变量
                    if result.success and result.data:
                        context.variables[f"step_{step_count}_result"] = result.data
                    
                    # 如果动作失败，进行反思
                    if not result.success:
                        logger.warning(f"Action failed: {result.message}")
                        # 可以在这里调用反思器分析失败原因
                
                # 更新最后决策
                last_decision = decision
                
                # 检查任务是否完成
                if await self._check_task_complete(goal, context, action_results):
                    logger.info("Task completed successfully")
                    break
            
            # 最终反思
            reflection = await self.reflector.reflect(
                task=task,
                action_results=action_results,
                current_state="任务执行完成"
            )
            
            # 判断是否成功
            all_success = all(r.success for r in action_results)
            task.status = TaskStatus.COMPLETED if all_success else TaskStatus.FAILED
            
            return {
                "success": all_success,
                "action_results": action_results,
                "reflection": reflection,
                "step_count": step_count,
                "variables": context.variables
            }
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            task.status = TaskStatus.FAILED
            return {
                "success": False,
                "error": str(e),
                "action_results": action_results,
                "step_count": step_count
            }
    
    async def _decide_next_step(
        self,
        goal: str,
        context: Context,
        available_tools: List[Dict[str, str]],
        last_decision: Optional[StepDecision] = None
    ) -> StepDecision:
        """
        决定下一步动作（调用LLM）
        
        Args:
            goal: 用户目标
            context: 执行上下文
            available_tools: 可用工具列表
            last_decision: 上一步决策（可选）
            
        Returns:
            步骤决策对象
        """
        # 生成决策Prompt
        prompt = get_agent_step_prompt(
            goal=goal,
            context=context,
            available_tools=available_tools,
            action_results=context.action_results,
            last_decision=last_decision
        )
        
        try:
            # 调用LLM生成决策
            response = await self.ollama_client.generate_async(prompt)
            
            # 解析决策响应
            decision = self._parse_decision_response(response, available_tools)
            return decision
            
        except Exception as e:
            logger.error(f"Error deciding next step: {e}")
            # 返回默认决策（停止执行）
            return StepDecision(
                should_continue=False,
                reasoning=f"决策过程出错: {str(e)}"
            )
    
    def _parse_decision_response(
        self,
        response: str,
        available_tools: List[Dict[str, str]]
    ) -> StepDecision:
        """
        解析LLM的决策响应
        
        Args:
            response: LLM响应文本
            available_tools: 可用工具列表
            
        Returns:
            步骤决策对象
        """
        import json
        import re
        
        try:
            # 尝试提取JSON
            json_str = self._extract_json_from_response(response)
            decision_data = json.loads(json_str)
            
            # 解析动作
            action = None
            if "action" in decision_data and decision_data["action"]:
                action_data = decision_data["action"]
                from .types import ActionType
                
                action_type_str = action_data.get("type", "gui")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    action_type = ActionType.GUI
                
                action = Action(
                    type=action_type,
                    tool=action_data.get("tool", ""),
                    args=action_data.get("args", {}),
                    description=action_data.get("description", "")
                )
            
            return StepDecision(
                action=action,
                should_continue=decision_data.get("should_continue", True),
                should_retry=decision_data.get("should_retry", False),
                should_skip=decision_data.get("should_skip", False),
                reasoning=decision_data.get("reasoning", ""),
                confidence=decision_data.get("confidence", 0.0),
                next_step_description=decision_data.get("next_step_description", "")
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse decision response: {e}")
            # 返回默认决策
            return StepDecision(
                should_continue=False,
                reasoning=f"解析决策响应失败: {str(e)}"
            )
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        从响应中提取JSON字符串
        
        Args:
            response: LLM响应文本
            
        Returns:
            提取的JSON字符串
        """
        response = response.strip()
        
        # 查找markdown代码块
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # 查找JSON对象
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return response
    
    async def _check_task_complete(
        self,
        goal: str,
        context: Context,
        action_results: List[ActionResult]
    ) -> bool:
        """
        检查任务是否完成
        
        Args:
            goal: 用户目标
            context: 执行上下文
            action_results: 动作执行结果列表
            
        Returns:
            任务是否完成
        """
        # 简单检查：如果所有动作都成功，认为任务完成
        if not action_results:
            return False
        
        # 可以添加更复杂的完成检查逻辑
        # 例如：调用LLM判断目标是否达成
        
        return all(r.success for r in action_results)


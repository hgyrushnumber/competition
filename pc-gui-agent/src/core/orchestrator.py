"""
协调器模块
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from .types import (
    Task, TaskStatus, ActionResult, Reflection, Context,
    AgentConfig, ToolUsage, ExecutionMode
)
from .planner import Planner
from .worker import Worker
from .reflector import Reflector
from .memory import Memory
from .workflow_executor import WorkflowExecutor
from .agent_executor import AgentExecutor
from ..llm.ollama_client import OllamaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """协调器"""
    
    def __init__(
        self,
        planner: Planner,
        worker: Worker,
        reflector: Reflector,
        memory: Memory,
        config: AgentConfig,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        初始化协调器
        
        Args:
            planner: 规划器
            worker: 执行器
            reflector: 反思器
            memory: 记忆模块
            config: Agent配置
            ollama_client: Ollama客户端（用于Agent模式，可选）
        """
        self.planner = planner
        self.worker = worker
        self.reflector = reflector
        self.memory = memory
        self.config = config
        self.ollama_client = ollama_client
        self._running_tasks: Dict[str, Task] = {}
        
        # 根据执行模式初始化执行器
        if config.execution_mode == ExecutionMode.WORKFLOW:
            self.workflow_executor = WorkflowExecutor(worker)
            self.agent_executor = None
            logger.info("Orchestrator initialized in WORKFLOW mode")
        elif config.execution_mode == ExecutionMode.AGENT:
            if ollama_client is None:
                raise ValueError("OllamaClient is required for AGENT mode")
            self.workflow_executor = None
            self.agent_executor = AgentExecutor(
                worker=worker,
                planner=planner,
                reflector=reflector,
                ollama_client=ollama_client
            )
            logger.info("Orchestrator initialized in AGENT mode")
        else:
            raise ValueError(f"Unknown execution mode: {config.execution_mode}")
    
    async def execute_task(self, goal: str) -> Dict[str, Any]:
        """
        执行任务（根据执行模式选择不同的执行器）
        
        Args:
            goal: 用户目标
            
        Returns:
            执行结果
        """
        logger.info(f"Starting task execution: {goal} (mode: {self.config.execution_mode.value})")
        
        try:
            # 根据执行模式选择执行器
            if self.config.execution_mode == ExecutionMode.WORKFLOW:
                return await self._execute_workflow_mode(goal)
            elif self.config.execution_mode == ExecutionMode.AGENT:
                return await self._execute_agent_mode(goal)
            else:
                raise ValueError(f"Unknown execution mode: {self.config.execution_mode}")
        
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"任务执行异常: {str(e)}"
            }
    
    async def _execute_workflow_mode(self, goal: str) -> Dict[str, Any]:
        """
        工作流模式执行
        
        Args:
            goal: 用户目标
            
        Returns:
            执行结果
        """
        if self.workflow_executor is None:
            raise ValueError("WorkflowExecutor is not initialized")
        
        # 加载工作流
        if self.config.workflow_path:
            workflow = self.workflow_executor.load_workflow_from_file(self.config.workflow_path)
        else:
            # 如果没有指定工作流路径，尝试从记忆或默认工作流匹配
            # 这里简化处理，实际可以更复杂
            raise ValueError("Workflow path not specified for WORKFLOW mode")
        
        # 执行工作流
        result = await self.workflow_executor.execute_workflow(workflow, goal)
        
        # 存储记忆
        if result.get("action_results"):
            tool_usages = [
                ToolUsage(
                    tool_name=r.action_id.split("_")[-1] if "_" in r.action_id else "unknown",
                    success=r.success,
                    execution_time=r.execution_time,
                    error=r.error
                )
                for r in result["action_results"]
            ]
            for tool_usage in tool_usages:
                await self.memory.store_tool_usage(tool_usage)
        
        return result
    
    async def _execute_agent_mode(self, goal: str) -> Dict[str, Any]:
        """
        Agent模式执行（逐步决策）
        
        Args:
            goal: 用户目标
            
        Returns:
            执行结果
        """
        if self.agent_executor is None:
            raise ValueError("AgentExecutor is not initialized")
        
        # 检索相似任务记忆
        similar_memories = await self.memory.retrieve_similar_tasks(goal, limit=3)
        if similar_memories:
            logger.info(f"Found {len(similar_memories)} similar tasks in memory")
        
        # 执行任务
        result = await self.agent_executor.execute_task(goal)
        
        # 存储记忆
        if result.get("action_results"):
            tool_usages = [
                ToolUsage(
                    tool_name=r.action_id.split("_")[-1] if "_" in r.action_id else "unknown",
                    success=r.success,
                    execution_time=r.execution_time,
                    error=r.error
                )
                for r in result["action_results"]
            ]
            for tool_usage in tool_usages:
                await self.memory.store_tool_usage(tool_usage)
        
        return result
    
    def _check_dependencies(
        self,
        subtask,
        all_subtasks: List
    ) -> bool:
        """
        检查子任务依赖是否满足
        
        Args:
            subtask: 当前子任务
            all_subtasks: 所有子任务列表
            
        Returns:
            依赖是否满足
        """
        if not subtask.dependencies:
            return True
        
        # 检查依赖的子任务是否已完成
        completed_ids = {st.id for st in all_subtasks if st.status == TaskStatus.COMPLETED}
        return all(dep_id in completed_ids for dep_id in subtask.dependencies)
    
    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id in self._running_tasks:
            # 这里可以实现暂停逻辑
            logger.info(f"Pausing task: {task_id}")
            return True
        return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            del self._running_tasks[task_id]
            logger.info(f"Cancelled task: {task_id}")
            return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            return {
                "id": task.id,
                "status": task.status.value,
                "goal": task.goal,
                "subtasks_count": len(task.subtasks)
            }
        return None


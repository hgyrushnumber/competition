"""
工作流执行器模块
支持预定义工作流的执行，包括步骤执行、条件判断和错误处理
"""
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .types import (
    WorkflowDefinition, WorkflowStep, Action, ActionResult, 
    Context, Task, TaskStatus
)
from .worker import Worker
from .error_handler import ErrorHandler, RecoveryStrategy
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, worker: Worker):
        """
        初始化工作流执行器
        
        Args:
            worker: 执行器实例
        """
        self.worker = worker
        self.error_handler = ErrorHandler()
    
    def load_workflow_from_file(self, file_path: str) -> WorkflowDefinition:
        """
        从文件加载工作流定义
        
        Args:
            file_path: 工作流定义文件路径（支持JSON和YAML）
            
        Returns:
            工作流定义对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return self._parse_workflow_definition(data)
    
    def load_workflow_from_dict(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """
        从字典加载工作流定义
        
        Args:
            data: 工作流定义字典
            
        Returns:
            工作流定义对象
        """
        return self._parse_workflow_definition(data)
    
    def _parse_workflow_definition(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """
        解析工作流定义数据
        
        Args:
            data: 工作流定义字典
            
        Returns:
            工作流定义对象
        """
        workflow_id = data.get("id", "workflow_1")
        name = data.get("name", "Unnamed Workflow")
        description = data.get("description", "")
        version = data.get("version", "1.0")
        variables = data.get("variables", {})
        on_complete = data.get("on_complete")
        on_error = data.get("on_error")
        
        # 解析步骤
        steps = []
        for step_data in data.get("steps", []):
            step = self._parse_workflow_step(step_data)
            steps.append(step)
        
        return WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            version=version,
            steps=steps,
            variables=variables,
            on_complete=on_complete,
            on_error=on_error
        )
    
    def _parse_workflow_step(self, step_data: Dict[str, Any]) -> WorkflowStep:
        """
        解析工作流步骤
        
        Args:
            step_data: 步骤数据字典
            
        Returns:
            工作流步骤对象
        """
        from .types import ActionType
        
        step_id = step_data.get("id", "")
        name = step_data.get("name", "")
        description = step_data.get("description", "")
        condition = step_data.get("condition")
        on_error = step_data.get("on_error")
        retry_count = step_data.get("retry_count", 0)
        timeout = step_data.get("timeout")
        
        # 解析动作
        action_data = step_data.get("action", {})
        action_type_str = action_data.get("type", "gui")
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            action_type = ActionType.GUI
        
        action = Action(
            type=action_type,
            tool=action_data.get("tool", ""),
            args=action_data.get("args", {}),
            description=action_data.get("description", description),
            timeout=timeout
        )
        
        return WorkflowStep(
            id=step_id,
            name=name,
            description=description,
            action=action,
            condition=condition,
            on_error=on_error,
            retry_count=retry_count,
            timeout=timeout
        )
    
    def _evaluate_condition(
        self,
        condition: str,
        context: Context
    ) -> bool:
        """
        评估条件表达式
        
        Args:
            condition: 条件表达式（Python表达式）
            context: 执行上下文
            
        Returns:
            条件是否满足
        """
        if not condition:
            return True
        
        try:
            # 构建评估环境
            eval_context = {
                "variables": context.variables,
                "action_results": context.action_results,
                "task": context.task,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
            }
            
            # 执行条件表达式
            result = eval(condition, {"__builtins__": {}}, eval_context)
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        goal: str,
        initial_context: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow: 工作流定义
            goal: 用户目标
            initial_context: 初始上下文（可选）
            
        Returns:
            执行结果
        """
        logger.info(f"Executing workflow: {workflow.name} (id: {workflow.id})")
        
        # 创建任务对象
        from .types import Task, Subtask
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
            context = Context(
                task=task,
                variables=workflow.variables.copy()
            )
        else:
            context = initial_context
            context.variables.update(workflow.variables)
        
        # 执行步骤
        action_results: List[ActionResult] = []
        executed_steps: List[str] = []
        
        try:
            for step in workflow.steps:
                # 检查条件
                if not self._evaluate_condition(step.condition, context):
                    logger.info(f"Skipping step {step.id} due to condition not met")
                    continue
                
                logger.info(f"Executing step: {step.name} (id: {step.id})")
                
                # 执行动作
                try:
                    result = await self._execute_step(step, context)
                    action_results.append(result)
                    context.action_results = action_results
                    
                    # 更新上下文变量
                    if result.success and result.data:
                        context.variables[f"step_{step.id}_result"] = result.data
                    
                    executed_steps.append(step.id)
                    
                    # 如果步骤失败，根据错误处理策略决定
                    if not result.success:
                        error_strategy = step.on_error or workflow.on_error
                        if error_strategy == "abort":
                            logger.error(f"Step {step.id} failed, aborting workflow")
                            break
                        elif error_strategy == "skip":
                            logger.warning(f"Step {step.id} failed, skipping")
                            continue
                        # 默认继续执行
                
                except Exception as e:
                    logger.error(f"Error executing step {step.id}: {e}")
                    error_strategy = step.on_error or workflow.on_error
                    if error_strategy == "abort":
                        raise
                    # 否则继续执行
                    
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            task.status = TaskStatus.FAILED
            return {
                "success": False,
                "error": str(e),
                "action_results": action_results,
                "executed_steps": executed_steps
            }
        
        # 执行完成处理
        if workflow.on_complete:
            try:
                self._execute_completion_handler(workflow.on_complete, context)
            except Exception as e:
                logger.warning(f"Error executing completion handler: {e}")
        
        # 判断是否成功
        all_success = all(r.success for r in action_results)
        task.status = TaskStatus.COMPLETED if all_success else TaskStatus.FAILED
        
        return {
            "success": all_success,
            "action_results": action_results,
            "executed_steps": executed_steps,
            "variables": context.variables
        }
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Context
    ) -> ActionResult:
        """
        执行单个步骤
        
        Args:
            step: 工作流步骤
            context: 执行上下文
            
        Returns:
            执行结果
        """
        # 使用重试机制执行
        max_retries = step.retry_count if step.retry_count > 0 else 1
        
        result = await self.worker.execute_with_retry(
            action=step.action,
            max_retries=max_retries,
            context=context
        )
        
        return result
    
    def _execute_completion_handler(
        self,
        handler: str,
        context: Context
    ):
        """
        执行完成处理程序
        
        Args:
            handler: 处理程序代码（Python代码字符串）
            context: 执行上下文
        """
        try:
            exec_context = {
                "variables": context.variables,
                "action_results": context.action_results,
                "task": context.task,
            }
            exec(handler, {"__builtins__": {}}, exec_context)
        except Exception as e:
            logger.error(f"Error executing completion handler: {e}")
            raise
    
    def match_workflow(
        self,
        goal: str,
        available_workflows: List[WorkflowDefinition]
    ) -> Optional[WorkflowDefinition]:
        """
        根据目标匹配工作流
        
        Args:
            goal: 用户目标
            available_workflows: 可用工作流列表
            
        Returns:
            匹配的工作流，如果没有匹配返回None
        """
        goal_lower = goal.lower()
        
        for workflow in available_workflows:
            # 简单匹配：检查目标是否包含工作流名称或描述中的关键词
            name_lower = workflow.name.lower()
            desc_lower = workflow.description.lower()
            
            if name_lower in goal_lower or desc_lower in goal_lower:
                return workflow
            
            # 检查工作流变量中是否有匹配关键词
            if "keywords" in workflow.variables:
                keywords = workflow.variables.get("keywords", [])
                if any(keyword.lower() in goal_lower for keyword in keywords):
                    return workflow
        
        return None


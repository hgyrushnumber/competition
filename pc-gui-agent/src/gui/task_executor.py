"""
任务执行器
处理异步任务执行并更新UI
"""
import asyncio
import threading
from typing import Optional, Callable, Dict, Any
from ..main import PCGUIAgent
from ..core.types import Task, ActionResult


class TaskExecutor:
    """任务执行器"""
    
    def __init__(
        self,
        agent: PCGUIAgent,
        on_task_start: Optional[Callable[[str, str], None]] = None,
        on_subtask_start: Optional[Callable[[str, str, str], None]] = None,
        on_action_start: Optional[Callable[[str, str, str, str, str], None]] = None,
        on_action_complete: Optional[Callable[[str, str, str, ActionResult], None]] = None,
        on_task_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_log: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        """
        初始化任务执行器
        
        Args:
            agent: Agent实例
            on_task_start: 任务开始回调 (task_id, goal)
            on_subtask_start: 子任务开始回调 (task_id, subtask_id, description)
            on_action_start: 动作开始回调 (task_id, subtask_id, action_id, description, tool)
            on_action_complete: 动作完成回调 (task_id, subtask_id, action_id, result)
            on_task_complete: 任务完成回调 (result_dict)
            on_log: 日志回调 (level, message, source)
        """
        self.agent = agent
        self.on_task_start = on_task_start
        self.on_subtask_start = on_subtask_start
        self.on_action_start = on_action_start
        self.on_action_complete = on_action_complete
        self.on_task_complete = on_task_complete
        self.on_log = on_log
        
        self._current_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._stop_requested = False
    
    async def execute_task_async(self, goal: str):
        """
        异步执行任务
        
        Args:
            goal: 任务目标
        """
        if self._is_running:
            if self.on_log:
                self.on_log("WARNING", "任务正在执行中，请等待完成", "TaskExecutor")
            return
        
        self._is_running = True
        self._stop_requested = False
        
        try:
            # 执行任务
            result = await self.agent.execute_task(goal)
            
            # 通知任务完成
            if self.on_task_complete:
                self.on_task_complete(result)
        
        except Exception as e:
            if self.on_log:
                self.on_log("ERROR", f"任务执行异常: {str(e)}", "TaskExecutor")
            if self.on_task_complete:
                self.on_task_complete({
                    "success": False,
                    "error": str(e),
                    "message": f"任务执行异常: {str(e)}"
                })
        
        finally:
            self._is_running = False
            self._stop_requested = False
    
    def execute_task(self, goal: str):
        """
        在后台线程执行任务（同步接口）
        
        Args:
            goal: 任务目标
        """
        if self._is_running:
            return
        
        # 在新线程中运行异步任务
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.execute_task_async(goal))
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def stop_task(self):
        """停止当前任务"""
        self._stop_requested = True
        if self.on_log:
            self.on_log("INFO", "停止任务请求已发送", "TaskExecutor")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running


"""
PC GUI Agent Flet应用
"""
import flet as ft
from typing import Optional, Dict, Any
from ..main import create_agent, PCGUIAgent
from .log_viewer import LogViewer
from .action_list import ActionList
from .task_executor import TaskExecutor
from ..core.types import ActionResult


class PCGUIAgentApp:
    """PC GUI Agent Flet应用"""
    
    def __init__(self, page: ft.Page):
        """
        初始化应用
        
        Args:
            page: Flet页面对象
        """
        self.page = page
        self.page.title = "PC GUI Agent"
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        
        # 初始化Agent
        self.agent: Optional[PCGUIAgent] = None
        self.task_executor: Optional[TaskExecutor] = None
        
        # 创建UI组件
        self.log_viewer = LogViewer(page)
        self.action_list = ActionList(page)
        
        # 构建界面
        self._build_ui()
        
        # 初始化Agent（异步）- 使用 page.run_task 在事件循环中执行
        page.run_task(self._init_agent)
    
    def _build_ui(self):
        """构建用户界面"""
        # 顶部工具栏
        self.task_input = ft.TextField(
            label="任务描述",
            hint_text="例如：在浏览器中打开百度并搜索'Python'",
            expand=True,
            on_submit=self._on_execute_task,
        )
        
        self.execute_btn = ft.ElevatedButton(
            text="执行任务",
            icon="play_arrow",  # 使用字符串图标名称
            on_click=self._on_execute_task,
        )
        
        self.stop_btn = ft.ElevatedButton(
            text="停止",
            icon="stop",  # 使用字符串图标名称
            on_click=self._on_stop_task,
            disabled=True,
        )
        
        self.clear_log_btn = ft.OutlinedButton(
            text="清空日志",
            icon="clear_all",  # 使用字符串图标名称
            on_click=self._on_clear_log,
        )
        
        toolbar = ft.Row(
            controls=[
                self.task_input,
                self.execute_btn,
                self.stop_btn,
                self.clear_log_btn,
            ],
            spacing=10,
        )
        
        # 中间区域：左侧动作列表，右侧日志
        middle_row = ft.Row(
            controls=[
                # 左侧：动作列表
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("任务执行列表", size=16, weight=ft.FontWeight.BOLD),
                            self.action_list.get_widget(),
                        ],
                        expand=True,
                    ),
                    expand=1,
                    padding=10,
                ),
                # 右侧：日志
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("实时日志", size=16, weight=ft.FontWeight.BOLD),
                            self.log_viewer.get_widget(),
                        ],
                        expand=True,
                    ),
                    expand=1,
                    padding=10,
                ),
            ],
            expand=True,
            spacing=10,
        )
        
        # 底部状态栏
        self.status_text = ft.Text("就绪", size=12)
        self.model_text = ft.Text("模型: 未连接", size=12)
        
        status_bar = ft.Row(
            controls=[
                self.status_text,
                ft.VerticalDivider(),
                self.model_text,
            ],
            spacing=10,
        )
        
        # 主布局
        self.page.add(
            ft.Column(
                controls=[
                    toolbar,
                    middle_row,
                    ft.Divider(),
                    status_bar,
                ],
                expand=True,
                spacing=10,
            )
        )
    
    async def _init_agent(self):
        """初始化Agent"""
        try:
            self.log_viewer.add_log("INFO", "正在初始化Agent...", "App")
            self.agent = create_agent()
            await self.agent.initialize()
            
            # 创建任务执行器
            self.task_executor = TaskExecutor(
                agent=self.agent,
                on_task_start=self._on_task_start,
                on_subtask_start=self._on_subtask_start,
                on_action_start=self._on_action_start,
                on_action_complete=self._on_action_complete,
                on_task_complete=self._on_task_complete,
                on_log=self._on_log,
            )
            
            # 更新状态
            model_name = self.agent.config.ollama_model
            self.model_text.value = f"模型: {model_name}"
            self.status_text.value = "就绪"
            self.page.update()
            
            self.log_viewer.add_log("INFO", "Agent初始化完成", "App")
        
        except Exception as e:
            self.log_viewer.add_log("ERROR", f"Agent初始化失败: {str(e)}", "App")
            self.status_text.value = f"初始化失败: {str(e)}"
            self.page.update()
    
    def _on_execute_task(self, e):
        """执行任务按钮点击事件"""
        goal = self.task_input.value.strip()
        if not goal:
            self.log_viewer.add_log("WARNING", "请输入任务描述", "App")
            return
        
        if not self.task_executor:
            self.log_viewer.add_log("ERROR", "Agent未初始化，请等待...", "App")
            return
        
        if self.task_executor.is_running():
            self.log_viewer.add_log("WARNING", "任务正在执行中，请等待完成", "App")
            return
        
        # 更新UI状态
        self.execute_btn.disabled = True
        self.stop_btn.disabled = False
        self.status_text.value = "执行中..."
        self.page.update()
        
        # 执行任务
        self.task_executor.execute_task(goal)
        self.log_viewer.add_log("INFO", f"开始执行任务: {goal}", "App")
    
    def _on_stop_task(self, e):
        """停止任务按钮点击事件"""
        if self.task_executor:
            self.task_executor.stop_task()
            self.log_viewer.add_log("INFO", "已请求停止任务", "App")
    
    def _on_clear_log(self, e):
        """清空日志按钮点击事件"""
        self.log_viewer.clear()
    
    def _on_task_start(self, task_id: str, goal: str):
        """任务开始回调"""
        self.action_list.add_task(task_id, goal)
        self.log_viewer.add_log("INFO", f"任务开始: {goal}", "TaskExecutor")
    
    def _on_subtask_start(self, task_id: str, subtask_id: str, description: str):
        """子任务开始回调"""
        self.action_list.add_subtask(task_id, subtask_id, description)
        self.log_viewer.add_log("INFO", f"子任务: {description}", "TaskExecutor")
    
    def _on_action_start(
        self,
        task_id: str,
        subtask_id: str,
        action_id: str,
        description: str,
        tool: str
    ):
        """动作开始回调"""
        self.action_list.add_action(
            task_id, subtask_id, action_id, description, tool, "running"
        )
        self.log_viewer.add_log("INFO", f"执行动作: {description} (工具: {tool})", "TaskExecutor")
    
    def _on_action_complete(
        self,
        task_id: str,
        subtask_id: str,
        action_id: str,
        result: ActionResult
    ):
        """动作完成回调"""
        status = "success" if result.success else "failed"
        message = result.message or (result.error or "完成")
        
        self.action_list.update_action_status(
            task_id, subtask_id, action_id, status, message
        )
        
        log_level = "INFO" if result.success else "ERROR"
        self.log_viewer.add_log(
            log_level,
            f"动作完成: {message}",
            "TaskExecutor"
        )
    
    def _on_task_complete(self, result: Dict):
        """任务完成回调"""
        success = result.get("success", False)
        message = result.get("message", "任务完成")
        
        # 更新UI状态
        self.execute_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_text.value = "就绪" if success else "任务失败"
        self.page.update()
        
        # 记录日志
        log_level = "INFO" if success else "ERROR"
        self.log_viewer.add_log(log_level, f"任务完成: {message}", "TaskExecutor")
        
        # 显示反思结果（如果有）
        if "reflection" in result:
            reflection = result["reflection"]
            self.log_viewer.add_log(
                "INFO",
                f"反思分析: {reflection.analysis[:100]}..." if len(reflection.analysis) > 100 else f"反思分析: {reflection.analysis}",
                "Reflector"
            )
    
    def _on_log(self, level: str, message: str, source: Optional[str] = None):
        """日志回调"""
        self.log_viewer.add_log(level, message, source)
    
    async def close(self):
        """关闭应用，清理资源"""
        if self.agent:
            await self.agent.close()


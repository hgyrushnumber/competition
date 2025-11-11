"""
动作列表组件
使用Flet显示任务执行过程中的动作列表
"""
from typing import List, Optional, Dict, Any
import flet as ft


class ActionList:
    """动作列表组件"""
    
    def __init__(self, page: ft.Page):
        """
        初始化动作列表
        
        Args:
            page: Flet页面对象
        """
        self.page = page
        self.action_list = ft.ListView(
            expand=True,
            spacing=5,
            padding=10
        )
        
        # 存储任务和动作的引用
        self.tasks: Dict[str, Dict[str, Any]] = {}
        
        # 创建容器
        self.container = ft.Container(
            content=self.action_list,
            expand=True,
            border=ft.border.all(1, "#e0e0e0"),  # 使用字符串颜色
            border_radius=5,
        )
    
    def add_task(self, task_id: str, goal: str):
        """
        添加新任务
        
        Args:
            task_id: 任务ID
            goal: 任务目标
        """
        # 创建任务标题
        task_title = ft.ExpansionTile(
            title=ft.Text(f"任务: {goal[:50]}..." if len(goal) > 50 else f"任务: {goal}"),
            subtitle=ft.Text(f"ID: {task_id}"),
            leading=ft.Icon(name="task", color="#1976d2"),  # 使用字符串图标名称
            initially_expanded=True,
        )
        
        # 存储任务信息
        self.tasks[task_id] = {
            "tile": task_title,
            "goal": goal,
            "subtasks": {}
        }
        
        # 添加到列表
        self.action_list.controls.append(task_title)
        self.page.update()
    
    def add_subtask(self, task_id: str, subtask_id: str, description: str):
        """
        添加子任务
        
        Args:
            task_id: 任务ID
            subtask_id: 子任务ID
            description: 子任务描述
        """
        if task_id not in self.tasks:
            return
        
        # 创建子任务标题
        subtask_title = ft.ExpansionTile(
            title=ft.Text(description),
            subtitle=ft.Text(f"子任务: {subtask_id}"),
            leading=ft.Icon(name="subdirectory_arrow_right", color="#616161"),  # 使用字符串图标名称
            initially_expanded=True,
        )
        
        # 存储子任务信息
        self.tasks[task_id]["subtasks"][subtask_id] = {
            "tile": subtask_title,
            "description": description,
            "actions": []
        }
        
        # 添加到任务的子任务列表
        task_tile = self.tasks[task_id]["tile"]
        if not hasattr(task_tile, 'controls'):
            task_tile.controls = []
        task_tile.controls.append(subtask_title)
        self.page.update()
    
    def add_action(
        self,
        task_id: str,
        subtask_id: str,
        action_id: str,
        description: str,
        tool: str,
        status: str = "pending"  # pending, running, success, failed
    ):
        """
        添加动作
        
        Args:
            task_id: 任务ID
            subtask_id: 子任务ID
            action_id: 动作ID
            description: 动作描述
            tool: 工具名称
            status: 状态（pending, running, success, failed）
        """
        if task_id not in self.tasks:
            return
        if subtask_id not in self.tasks[task_id]["subtasks"]:
            return
        
        # 状态图标和颜色（使用字符串图标名称和颜色值）
        status_config = {
            "pending": ("schedule", "#9e9e9e"),      # GREY
            "running": ("autorenew", "#1976d2"),     # BLUE
            "success": ("check_circle", "#388e3c"),  # GREEN
            "failed": ("error", "#d32f2f"),          # RED
        }
        
        icon_name, icon_color = status_config.get(status, ("help", "#9e9e9e"))
        
        # 创建动作项
        action_item = ft.ListTile(
            leading=ft.Icon(name=icon_name, color=icon_color),
            title=ft.Text(description),
            subtitle=ft.Text(f"工具: {tool}"),
            dense=True,
        )
        
        # 存储动作信息
        self.tasks[task_id]["subtasks"][subtask_id]["actions"].append({
            "item": action_item,
            "action_id": action_id,
            "description": description,
            "tool": tool,
            "status": status
        })
        
        # 添加到子任务的动作列表
        subtask_tile = self.tasks[task_id]["subtasks"][subtask_id]["tile"]
        if not hasattr(subtask_tile, 'controls'):
            subtask_tile.controls = []
        subtask_tile.controls.append(action_item)
        self.page.update()
    
    def update_action_status(
        self,
        task_id: str,
        subtask_id: str,
        action_id: str,
        status: str,
        message: Optional[str] = None
    ):
        """
        更新动作状态
        
        Args:
            task_id: 任务ID
            subtask_id: 子任务ID
            action_id: 动作ID
            status: 新状态
            message: 状态消息（可选）
        """
        if task_id not in self.tasks:
            return
        if subtask_id not in self.tasks[task_id]["subtasks"]:
            return
        
        # 查找动作
        for action in self.tasks[task_id]["subtasks"][subtask_id]["actions"]:
            if action["action_id"] == action_id:
                # 更新状态
                action["status"] = status
                
                # 更新图标和颜色（使用字符串图标名称和颜色值）
                status_config = {
                    "pending": ("schedule", "#9e9e9e"),      # GREY
                    "running": ("autorenew", "#1976d2"),     # BLUE
                    "success": ("check_circle", "#388e3c"),  # GREEN
                    "failed": ("error", "#d32f2f"),          # RED
                }
                
                icon_name, icon_color = status_config.get(status, ("help", "#9e9e9e"))
                action["item"].leading = ft.Icon(name=icon_name, color=icon_color)
                
                # 更新消息
                if message:
                    if action["item"].subtitle:
                        action["item"].subtitle.value = f"工具: {action['tool']} - {message}"
                    else:
                        action["item"].subtitle = ft.Text(f"工具: {action['tool']} - {message}")
                
                self.page.update()
                break
    
    def clear(self):
        """清空动作列表"""
        self.action_list.controls.clear()
        self.tasks.clear()
        self.page.update()
    
    def get_widget(self) -> ft.Container:
        """
        获取动作列表组件
        
        Returns:
            Flet容器组件
        """
        return self.container


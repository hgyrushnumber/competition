"""
日志查看器组件
使用Flet显示实时日志
"""
import logging
from typing import Optional
import flet as ft
from datetime import datetime


class LogViewer:
    """日志查看器"""
    
    def __init__(self, page: ft.Page):
        """
        初始化日志查看器
        
        Args:
            page: Flet页面对象
        """
        self.page = page
        self.log_list = ft.ListView(
            expand=True,
            spacing=2,
            padding=10
        )
        
        # 创建容器
        self.container = ft.Container(
            content=self.log_list,
            expand=True,
            border=ft.border.all(1, "#e0e0e0"),  # 使用字符串颜色
            border_radius=5,
        )
        
        # 日志级别颜色映射（使用字符串颜色值）
        self.log_colors = {
            "DEBUG": "#757575",      # GREY_600
            "INFO": "#1976d2",       # BLUE_700
            "WARNING": "#f57c00",    # ORANGE_700
            "ERROR": "#d32f2f",      # RED_700
            "CRITICAL": "#b71c1c",   # RED_900
        }
    
    def add_log(self, level: str, message: str, source: Optional[str] = None):
        """
        添加日志条目
        
        Args:
            level: 日志级别
            message: 日志消息
            source: 日志来源（可选）
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.log_colors.get(level.upper(), "#616161")  # 默认 GREY_700
        
        # 构建日志文本
        log_text = f"[{timestamp}] "
        if source:
            log_text += f"[{source}] "
        log_text += message
        
        # 创建日志条目
        log_entry = ft.Text(
            value=log_text,
            color=color,
            size=12,
            selectable=True,
        )
        
        # 添加到列表
        self.log_list.controls.append(log_entry)
        
        # 自动滚动到底部
        self.log_list.controls.append(ft.Container(height=0))  # 占位符，确保滚动
        
        # 更新页面
        self.page.update()
    
    def clear(self):
        """清空日志"""
        self.log_list.controls.clear()
        self.page.update()
    
    def get_widget(self) -> ft.Container:
        """
        获取日志查看器组件
        
        Returns:
            Flet容器组件
        """
        return self.container


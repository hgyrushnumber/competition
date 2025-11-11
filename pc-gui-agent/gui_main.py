"""
PC GUI Agent GUI应用入口
使用Flet创建桌面应用程序
"""
import flet as ft
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.gui.app import PCGUIAgentApp


def main(page: ft.Page):
    """主函数"""
    app = PCGUIAgentApp(page)
    # Flet 会在应用退出时自动清理资源
    # 如果需要特殊清理，可以在应用退出前处理


if __name__ == "__main__":
    # 启动Flet应用（桌面模式）
    ft.app(target=main)


"""
Python MCP 服务器 - 文件系统工具

使用 FastMCP 创建一个简单的文件系统 MCP 服务器，提供基本的文件操作工具。

运行方式：
    python examples/python_mcp_server.py

或者通过环境变量：
    $env:MCP_SERVER_COMMAND="python examples/python_mcp_server.py"
"""
import sys
from pathlib import Path
from typing import Any

# 尝试导入 FastMCP
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("错误: 无法导入 mcp.server.fastmcp", file=sys.stderr)
    print("请安装 MCP 包: pip install mcp", file=sys.stderr)
    sys.exit(1)

# 创建 MCP 服务器
mcp = FastMCP("Python FileSystem Server")


@mcp.tool()
def read_file(path: str) -> str:
    """
    读取文件内容
    
    Args:
        path: 文件路径（相对路径或绝对路径）
    
    Returns:
        文件内容（字符串）
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {path}")
        
        # 读取文件内容
        content = file_path.read_text(encoding='utf-8')
        return content
    except Exception as e:
        return f"错误: {str(e)}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    写入文件内容
    
    Args:
        path: 文件路径（相对路径或绝对路径）
        content: 要写入的内容（字符串）
    
    Returns:
        成功消息或错误信息
    """
    try:
        file_path = Path(path)
        
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        file_path.write_text(content, encoding='utf-8')
        return f"成功写入文件: {path}"
    except Exception as e:
        return f"错误: {str(e)}"


@mcp.tool()
def list_directory(path: str = ".") -> str:
    """
    列出目录内容
    
    Args:
        path: 目录路径（默认为当前目录）
    
    Returns:
        目录内容列表（字符串格式）
    """
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")
        if not dir_path.is_dir():
            raise ValueError(f"路径不是目录: {path}")
        
        # 列出目录内容
        items = []
        for item in sorted(dir_path.iterdir()):
            item_type = "目录" if item.is_dir() else "文件"
            size = item.stat().st_size if item.is_file() else 0
            items.append(f"{item_type:6s}  {item.name:50s}  {size:>10d} bytes")
        
        result = f"目录: {path}\n"
        result += "=" * 80 + "\n"
        result += f"{'类型':6s}  {'名称':50s}  {'大小':>10s}\n"
        result += "-" * 80 + "\n"
        if items:
            result += "\n".join(items)
        else:
            result += "(空目录)"
        result += "\n"
        
        return result
    except Exception as e:
        return f"错误: {str(e)}"


@mcp.tool()
def file_exists(path: str) -> bool:
    """
    检查文件或目录是否存在
    
    Args:
        path: 文件或目录路径
    
    Returns:
        如果存在返回 True，否则返回 False
    """
    try:
        file_path = Path(path)
        return file_path.exists()
    except Exception:
        return False


@mcp.tool()
def get_file_info(path: str) -> str:
    """
    获取文件或目录的详细信息
    
    Args:
        path: 文件或目录路径
    
    Returns:
        文件或目录的详细信息（字符串格式）
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"错误: 路径不存在: {path}"
        
        info = []
        info.append(f"路径: {file_path.absolute()}")
        info.append(f"类型: {'目录' if file_path.is_dir() else '文件'}")
        
        if file_path.is_file():
            stat = file_path.stat()
            info.append(f"大小: {stat.st_size} bytes")
            info.append(f"修改时间: {stat.st_mtime}")
        
        return "\n".join(info)
    except Exception as e:
        return f"错误: {str(e)}"


if __name__ == "__main__":
    # 运行服务器（使用 stdio 传输）
    mcp.run()


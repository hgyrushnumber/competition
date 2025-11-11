"""
日志工具
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def get_logger(name: str, level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        
    Returns:
        Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


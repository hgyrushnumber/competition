"""
错误处理
"""


class AgentError(Exception):
    """Agent基础异常"""
    pass


class PlanningError(AgentError):
    """规划错误"""
    pass


class ExecutionError(AgentError):
    """执行错误"""
    pass


class ReflectionError(AgentError):
    """反思错误"""
    pass


class ToolError(AgentError):
    """工具错误"""
    pass


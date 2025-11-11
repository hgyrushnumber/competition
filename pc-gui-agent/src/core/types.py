"""
核心类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TypedDict, Literal
from enum import Enum
from datetime import datetime


class ActionType(str, Enum):
    """动作类型"""
    GUI = "gui"  # GUI操作
    CODE = "code"  # 代码执行
    MCP = "mcp"  # MCP工具调用


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """执行模式"""
    WORKFLOW = "workflow"  # 工作流模式：预定义步骤
    AGENT = "agent"  # Agent模式：LLM实时指挥


@dataclass
class Action:
    """动作定义"""
    type: ActionType
    tool: str  # 工具名称
    args: Dict[str, Any]  # 工具参数
    description: str  # 动作描述
    dependencies: List[str] = field(default_factory=list)  # 依赖的动作ID
    timeout: Optional[int] = None  # 超时时间（秒）


@dataclass
class Subtask:
    """子任务"""
    id: str
    description: str
    actions: List[Action]
    dependencies: List[str] = field(default_factory=list)  # 依赖的子任务ID
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class Task:
    """任务"""
    id: str
    goal: str  # 用户目标
    subtasks: List[Subtask]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ExecutionPlan(TypedDict):
    """执行计划"""
    task_id: str
    goal: str
    subtasks: List[Dict[str, Any]]
    estimated_time: Optional[int]  # 预估时间（秒）


@dataclass
class ActionResult:
    """动作执行结果"""
    action_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: str = ""
    execution_time: float = 0.0  # 执行时间（秒）
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Reflection:
    """反思结果"""
    task_id: str
    success: bool
    analysis: str  # 分析结果
    suggestions: List[str]  # 调整建议
    needs_replan: bool = False  # 是否需要重规划
    confidence: float = 0.0  # 置信度 (0-1)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentConfig:
    """Agent配置"""
    # LLM配置
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:latest"
    
    # 执行配置
    execution_mode: ExecutionMode = ExecutionMode.AGENT  # 执行模式：workflow 或 agent
    max_retries: int = 3
    retry_delay: float = 1.0  # 重试延迟（秒）
    action_timeout: int = 30  # 动作超时（秒）
    
    # 数据库配置
    database_path: str = "./data/memory.db"
    
    # MCP配置
    mcp_enabled: bool = False  # 是否启用MCP
    mcp_server_command: Optional[str] = None  # MCP服务器命令（如 "python -m mcp.server.filesystem"）
    mcp_transport: str = "stdio"  # 传输方式（stdio 或 http）
    use_mcp_browser: bool = False  # 是否使用MCP Puppeteer控制浏览器（替代Playwright）
    mcp_puppeteer_command: Optional[str] = None  # Puppeteer MCP服务器命令（如 "npx -y @modelcontextprotocol/server-puppeteer"）
    
    # 工作流配置（仅workflow模式）
    workflow_path: Optional[str] = None  # 工作流定义文件路径
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    task_id: str
    task_goal: str
    task_result: Dict[str, Any]
    reflection: Optional[Dict[str, Any]] = None
    tool_usage: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolUsage:
    """工具使用记录"""
    tool_name: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Context:
    """执行上下文"""
    task: Task
    current_subtask_id: Optional[str] = None
    action_results: List[ActionResult] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    screen_state: Optional[Dict[str, Any]] = None  # 当前屏幕状态


@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    id: str
    name: str
    description: str
    action: Action
    condition: Optional[str] = None  # 条件表达式（可选）
    on_error: Optional[str] = None  # 错误处理策略：retry, skip, abort
    retry_count: int = 0  # 重试次数
    timeout: Optional[int] = None  # 超时时间（秒）


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str
    version: str = "1.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)  # 工作流变量
    on_complete: Optional[str] = None  # 完成时的处理
    on_error: Optional[str] = None  # 全局错误处理


@dataclass
class StepDecision:
    """Agent模式的步骤决策"""
    action: Optional[Action] = None  # 下一步动作
    should_continue: bool = True  # 是否继续执行
    should_retry: bool = False  # 是否重试上一步
    should_skip: bool = False  # 是否跳过当前步骤
    reasoning: str = ""  # 决策理由
    confidence: float = 0.0  # 置信度 (0-1)
    next_step_description: str = ""  # 下一步描述


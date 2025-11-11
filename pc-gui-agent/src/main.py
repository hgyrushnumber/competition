"""
PC GUI Agent 主入口
"""
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .core.types import AgentConfig, ExecutionMode
from .core.orchestrator import Orchestrator
from .core.planner import Planner
from .core.worker import Worker
from .core.reflector import Reflector
from .core.memory import Memory
from .llm.ollama_client import OllamaClient
from .tools.registry import get_registry, ToolRegistry
from .tools.gui_tools import (
    NavigateTool, ClickTool, InputTool, ScrollTool, ScreenshotTool, WaitTool
)
from .utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger(__name__)


class PCGUIAgent:
    """PC GUI Agent主类"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化Agent
        
        Args:
            config: Agent配置（可选，默认从环境变量读取）
        """
        # 加载配置
        if config is None:
            # 检查环境变量
            env_model = os.getenv("OLLAMA_MODEL")
            default_model = "llama3.1:latest"
            if env_model:
                logger.info(f"Found OLLAMA_MODEL in environment: {env_model}")
            else:
                logger.info(f"No OLLAMA_MODEL in environment, using default: {default_model}")
            
            # 解析执行模式
            execution_mode_str = os.getenv("EXECUTION_MODE", "agent").lower()
            if execution_mode_str == "workflow":
                execution_mode = ExecutionMode.WORKFLOW
            else:
                execution_mode = ExecutionMode.AGENT
            
            config = AgentConfig(
                ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                ollama_model=env_model if env_model else default_model,
                execution_mode=execution_mode,
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
                action_timeout=int(os.getenv("ACTION_TIMEOUT", "30")),
                database_path=os.getenv("DATABASE_PATH", "./data/memory.db"),
                mcp_enabled=os.getenv("MCP_ENABLED", "false").lower() == "true",
                mcp_server_command=os.getenv("MCP_SERVER_COMMAND"),
                mcp_transport=os.getenv("MCP_TRANSPORT", "stdio"),
                use_mcp_browser=os.getenv("USE_MCP_BROWSER", "false").lower() == "true",
                mcp_puppeteer_command=os.getenv("MCP_PUPPETEER_COMMAND"),
                workflow_path=os.getenv("WORKFLOW_PATH"),  # 工作流文件路径（仅workflow模式）
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                log_file=os.getenv("LOG_FILE")
            )
        
        self.config = config
        
        # 初始化组件
        logger.info(f"Using Ollama model: {config.ollama_model}")
        self.ollama_client = OllamaClient(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )
        
        self.memory = Memory(database_path=config.database_path)
        
        self.tool_registry = get_registry()
        self._register_default_tools()
        
        # MCP客户端（如果启用）
        self.mcp_client = None
        if config.mcp_enabled and config.mcp_server_command:
            from src.mcp.client import MCPClient
            self.mcp_client = MCPClient(
                server_command=config.mcp_server_command,
                transport=config.mcp_transport
            )
        
        self.planner = Planner(
            ollama_client=self.ollama_client,
            tool_registry=self.tool_registry
        )
        
        self.worker = Worker(
            tool_registry=self.tool_registry,
            ollama_client=self.ollama_client
        )
        
        self.reflector = Reflector(ollama_client=self.ollama_client)
        
        self.orchestrator = Orchestrator(
            planner=self.planner,
            worker=self.worker,
            reflector=self.reflector,
            memory=self.memory,
            config=config,
            ollama_client=self.ollama_client  # 传递Ollama客户端用于Agent模式
        )
    
    def _register_default_tools(self) -> None:
        """注册默认工具"""
        # 如果 MCP 客户端可用，传入给 GUI 工具以支持 MCP Puppeteer
        mcp_client = self.mcp_client if hasattr(self, 'mcp_client') else None
        tools = [
            NavigateTool(mcp_client=mcp_client),
            ClickTool(mcp_client=mcp_client),
            InputTool(mcp_client=mcp_client),
            ScrollTool(mcp_client=mcp_client),
            ScreenshotTool(mcp_client=mcp_client),
            WaitTool(mcp_client=mcp_client)
        ]
        self.tool_registry.register_multiple(tools)
        logger.info(f"Registered {len(tools)} default tools")
    
    async def initialize(self) -> None:
        """初始化Agent（初始化数据库等）"""
        await self.memory.initialize()
        
        # 检查Ollama连接
        if not self.ollama_client.check_connection():
            logger.warning("Ollama connection check failed, but continuing...")
        
        # 初始化MCP（如果启用）
        if self.mcp_client:
            try:
                connected = await self.mcp_client.connect()
                if connected:
                    # 发现并注册MCP工具
                    from src.tools.mcp_tool import create_mcp_tools
                    mcp_tools = create_mcp_tools(self.mcp_client)
                    self.tool_registry.register_multiple(mcp_tools)
                    logger.info(f"Registered {len(mcp_tools)} MCP tools")
                else:
                    logger.warning("Failed to connect to MCP server")
            except Exception as e:
                logger.error(f"Error initializing MCP: {e}")
        
        logger.info("Agent initialized")
    
    async def execute_task(self, goal: str) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            goal: 用户目标
            
        Returns:
            执行结果
        """
        return await self.orchestrator.execute_task(goal)
    
    async def close(self) -> None:
        """关闭Agent（清理资源）"""
        # 关闭MCP客户端
        if self.mcp_client:
            await self.mcp_client.disconnect()
        
        # 关闭所有GUI工具中的浏览器
        from .tools.gui_tools import GUITools
        gui_tools_instance = GUITools()
        await gui_tools_instance.close()
        logger.info("Agent closed")


def create_agent(config: Optional[AgentConfig] = None) -> PCGUIAgent:
    """
    创建Agent实例的工厂函数
    
    Args:
        config: Agent配置（可选）
        
    Returns:
        Agent实例
    """
    return PCGUIAgent(config)


# 导出主要类和接口
__all__ = [
    "PCGUIAgent",
    "create_agent",
    "AgentConfig",
    "Orchestrator",
    "Planner",
    "Worker",
    "Reflector",
    "Memory",
    "OllamaClient",
    "ToolRegistry"
]


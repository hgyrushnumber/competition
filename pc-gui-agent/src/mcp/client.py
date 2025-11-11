"""
MCP客户端
使用官方 MCP Python SDK 实现客户端，用于连接MCP服务器并调用工具
参考：https://mcp-docs.cn/quickstart/client
"""
import shlex
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

# 尝试从本地 python-sdk 导入，如果失败则从已安装的包导入
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import mcp.types as mcp_types
except ImportError:
    # 如果本地导入失败，尝试从 python-sdk 路径导入
    import sys
    from pathlib import Path
    
    # 添加 python-sdk 的 src 目录到路径
    python_sdk_path = Path(__file__).parent.parent.parent / "python-sdk" / "src"
    if python_sdk_path.exists():
        sys.path.insert(0, str(python_sdk_path))
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import mcp.types as mcp_types
    else:
        raise ImportError(
            "Cannot import MCP SDK. Please install mcp package or ensure python-sdk is available."
        )

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    MCP客户端包装类，使用官方 SDK
    
    参考 MCP 官方文档：https://mcp-docs.cn/quickstart/client
    使用 AsyncExitStack 进行资源管理（最佳实践）
    """
    
    def __init__(
        self,
        server_command: Optional[str] = None,
        transport: str = "stdio"  # stdio 或 http
    ):
        """
        初始化MCP客户端
        
        Args:
            server_command: MCP服务器命令（如 "python -m mcp.server.filesystem"）
            transport: 传输方式（stdio 或 http，目前仅支持 stdio）
        """
        self.server_command = server_command
        self.transport = transport
        self._stdio_params: Optional[StdioServerParameters] = None
        self._exit_stack = AsyncExitStack()  # 使用 AsyncExitStack 管理资源（最佳实践）
        self._session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self.connected = False
        self._tools: List[Dict[str, Any]] = []
        
        logger.debug(f"MCPClient initialized: server_command={server_command}, transport={transport}")
    
    def _parse_server_command(self, server_command: str) -> StdioServerParameters:
        """
        解析服务器命令字符串为 StdioServerParameters
        
        Args:
            server_command: 服务器命令字符串，如 "python -m mcp.server.filesystem"
            
        Returns:
            StdioServerParameters 对象
        """
        logger.debug(f"Parsing server command: {server_command}")
        parts = shlex.split(server_command)
        if not parts:
            logger.error("Empty server command after parsing")
            raise ValueError("Empty server command")
        
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        logger.debug(f"Parsed command: command={command}, args={args}")
        
        stdio_params = StdioServerParameters(
            command=command,
            args=args
        )
        
        logger.debug(f"Created StdioServerParameters: command={stdio_params.command}, args={stdio_params.args}")
        return stdio_params
    
    async def connect(self) -> bool:
        """
        连接到MCP服务器
        
        Returns:
            是否连接成功
        """
        if not self.server_command:
            logger.warning("MCP server command not specified, skipping connection")
            return False
        
        if self.transport != "stdio":
            logger.error(f"Transport '{self.transport}' not implemented yet. Only 'stdio' is supported.")
            return False
        
        try:
            logger.debug("Starting MCP connection process...")
            
            # 解析服务器命令
            logger.debug("Step 1: Parsing server command")
            self._stdio_params = self._parse_server_command(self.server_command)
            logger.debug(f"Server parameters: command={self._stdio_params.command}, args={self._stdio_params.args}")
            
            # 使用 AsyncExitStack 管理资源（参考 MCP 官方文档最佳实践）
            # 1. 创建 stdio 客户端上下文并进入
            logger.debug("Step 2: Creating stdio_client context")
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(self._stdio_params)
            )
            self._read_stream, self._write_stream = stdio_transport
            logger.debug("stdio_client context entered successfully, streams obtained")
            
            # 2. 创建客户端会话并进入
            logger.debug("Step 3: Creating ClientSession context")
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(self._read_stream, self._write_stream)
            )
            logger.debug("ClientSession context entered successfully")
            
            # 3. 初始化连接
            logger.debug("Step 4: Initializing MCP session (sending initialize request)")
            await self._session.initialize()
            logger.debug("MCP session initialized successfully")
            
            self.connected = True
            logger.info("MCP client connected via stdio using official SDK")
            
            # 4. 发现可用工具
            logger.debug("Step 5: Discovering available tools")
            await self.list_tools()
            
            logger.debug("MCP connection process completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}", exc_info=True)
            logger.debug(f"Connection error details: type={type(e).__name__}, message={str(e)}")
            await self._cleanup()
            return False
    
    async def _cleanup(self):
        """
        清理资源
        
        使用 AsyncExitStack 自动清理所有资源（参考 MCP 官方文档最佳实践）
        """
        # 如果已经断开连接，直接返回
        if not self.connected:
            logger.debug("Already disconnected, skipping cleanup")
            return
        
        logger.debug("Starting cleanup process...")
        try:
            # 先标记为未连接，避免在清理过程中再次调用
            self.connected = False
            
            # AsyncExitStack 会自动以相反的顺序清理所有资源
            # 1. 关闭 ClientSession
            # 2. 关闭 stdio_client（会关闭进程和流）
            logger.debug("Closing AsyncExitStack (will close ClientSession and stdio_client in reverse order)")
            
            # 检查 exit_stack 是否存在且未关闭
            if self._exit_stack is not None:
                try:
                    await self._exit_stack.aclose()
                    logger.debug("AsyncExitStack closed successfully")
                except Exception as e:
                    # 忽略 GeneratorExit 和 RuntimeError（这些是正常的关闭异常）
                    if isinstance(e, (GeneratorExit, RuntimeError)):
                        logger.debug(f"Expected exception during cleanup: {type(e).__name__}")
                    else:
                        logger.warning(f"Unexpected error during AsyncExitStack cleanup: {e}")
                        logger.debug(f"Cleanup error details: type={type(e).__name__}, message={str(e)}", exc_info=True)
            else:
                logger.debug("ExitStack is None, skipping cleanup")
                
        except Exception as e:
            # 忽略 GeneratorExit 和 RuntimeError（这些是正常的关闭异常）
            if isinstance(e, (GeneratorExit, RuntimeError)):
                logger.debug(f"Expected exception during cleanup: {type(e).__name__}")
            else:
                logger.warning(f"Error during cleanup: {e}")
                logger.debug(f"Cleanup error details: type={type(e).__name__}, message={str(e)}", exc_info=True)
        finally:
            # 重置状态
            logger.debug("Resetting client state")
            self._session = None
            self._read_stream = None
            self._write_stream = None
            self.connected = False
            # 重新创建 exit_stack 以便下次连接
            self._exit_stack = AsyncExitStack()
            logger.debug("Cleanup process completed")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            工具列表（转换为字典格式以保持兼容性）
        """
        if not self._session or not self.connected:
            logger.warning("MCP client not connected, cannot list tools")
            logger.debug(f"Connection state: session={self._session is not None}, connected={self.connected}")
            return []
        
        try:
            logger.debug("Sending list_tools request to MCP server")
            result = await self._session.list_tools()
            logger.debug(f"Received list_tools response: {len(result.tools)} tools found")
            
            # 将 Tool 对象转换为字典格式以保持兼容性
            self._tools = []
            for idx, tool in enumerate(result.tools):
                logger.debug(f"Processing tool {idx + 1}/{len(result.tools)}: {tool.name}")
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema
                }
                self._tools.append(tool_dict)
                logger.debug(f"Tool '{tool.name}': description='{tool.description or 'N/A'}'")
                if hasattr(tool.inputSchema, 'model_dump'):
                    logger.debug(f"Tool '{tool.name}' inputSchema keys: {list(tool.inputSchema.model_dump().keys())}")
            
            logger.info(f"Found {len(self._tools)} MCP tools")
            logger.debug(f"Tools list: {[t['name'] for t in self._tools]}")
            return self._tools
        
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}", exc_info=True)
            logger.debug(f"list_tools error details: type={type(e).__name__}, message={str(e)}")
            return []
    
    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果（转换为字典格式以保持兼容性）
        """
        if not self._session or not self.connected:
            logger.error(f"Cannot call tool '{name}': MCP client not connected")
            logger.debug(f"Connection state: session={self._session is not None}, connected={self.connected}")
            raise RuntimeError("MCP client not connected")
        
        try:
            logger.debug(f"Calling MCP tool '{name}' with arguments: {arguments}")
            result = await self._session.call_tool(name, arguments or {})
            logger.debug(f"Received tool call response for '{name}': isError={result.isError}, content_count={len(result.content) if result.content else 0}")
            
            # 将 CallToolResult 转换为字典格式以保持兼容性
            result_dict: Dict[str, Any] = {}
            
            # 处理内容
            if result.content:
                logger.debug(f"Processing {len(result.content)} content items")
                # 提取文本内容
                content_list = []
                for idx, content_item in enumerate(result.content):
                    logger.debug(f"Processing content item {idx + 1}/{len(result.content)}: type={type(content_item).__name__}")
                    if isinstance(content_item, mcp_types.TextContent):
                        text_preview = content_item.text[:100] + "..." if len(content_item.text) > 100 else content_item.text
                        logger.debug(f"TextContent: length={len(content_item.text)}, preview='{text_preview}'")
                        content_list.append({
                            "type": "text",
                            "text": content_item.text
                        })
                    elif isinstance(content_item, mcp_types.ImageContent):
                        logger.debug(f"ImageContent: mimeType={content_item.mimeType}, data_length={len(content_item.data) if content_item.data else 0}")
                        content_list.append({
                            "type": "image",
                            "data": content_item.data,
                            "mimeType": content_item.mimeType
                        })
                    else:
                        # 其他类型的内容
                        content_type = getattr(content_item, "type", "unknown")
                        logger.debug(f"Other content type: {content_type}")
                        content_dict = {"type": content_type}
                        if hasattr(content_item, 'model_dump'):
                            content_dict.update(content_item.model_dump())
                        content_list.append(content_dict)
                
                result_dict["content"] = content_list
                
                # 为了兼容性，提取第一个文本内容作为主要数据
                if content_list and content_list[0].get("type") == "text":
                    result_dict["text"] = content_list[0]["text"]
                    logger.debug(f"Extracted text field: length={len(result_dict['text'])}")
            
            # 处理结构化内容
            if result.structuredContent:
                logger.debug(f"Processing structuredContent: {type(result.structuredContent).__name__}")
                result_dict["structuredContent"] = result.structuredContent
            
            # 处理错误
            if result.isError:
                logger.warning(f"Tool '{name}' returned an error")
                result_dict["isError"] = True
                if result.content:
                    for content_item in result.content:
                        if isinstance(content_item, mcp_types.TextContent):
                            result_dict["error"] = content_item.text
                            logger.debug(f"Error message: {content_item.text}")
                            break
            
            logger.debug(f"Tool call '{name}' completed successfully: result_keys={list(result_dict.keys())}")
            return result_dict
        
        except Exception as e:
            logger.error(f"Failed to call MCP tool '{name}': {e}", exc_info=True)
            logger.debug(f"Tool call error details: tool={name}, arguments={arguments}, error_type={type(e).__name__}, error_message={str(e)}")
            raise
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取已发现的工具列表
        
        Returns:
            工具列表
        """
        return self._tools
    
    async def disconnect(self):
        """
        断开MCP服务器连接
        
        注意：只有在明确需要断开连接时才调用此方法（例如 Agent 关闭时）
        不要在任务执行期间调用，否则会导致连接意外关闭
        """
        # 如果已经断开连接，直接返回
        if not self.connected:
            logger.debug("Already disconnected, skipping disconnect")
            return
        
        logger.debug("Disconnecting MCP client...")
        try:
            await self._cleanup()
            logger.info("MCP client disconnected")
            logger.debug("Disconnect completed")
        except Exception as e:
            # 记录错误但不抛出异常，确保状态被正确重置
            logger.warning(f"Error during disconnect: {e}")
            logger.debug(f"Disconnect error details: type={type(e).__name__}, message={str(e)}", exc_info=True)


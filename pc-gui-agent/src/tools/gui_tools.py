"""
GUI操作工具（基于Playwright或MCP Puppeteer）
"""
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from .base_tool import BaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GUITools(BaseTool):
    """GUI操作工具集合"""
    
    # 单例模式，确保只有一个浏览器实例
    _instance: Optional['GUITools'] = None
    
    def __new__(cls, mcp_client=None):
        """
        单例模式：接受 mcp_client 参数（即使单例模式下，第一次创建后后续调用会忽略参数）
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, mcp_client=None):
        """
        初始化 GUITools 实例
        
        在单例模式下：
        - 如果实例未初始化，进行完整初始化
        - 如果实例已初始化，但提供了新的 mcp_client，更新它（如果当前 mcp_client 为 None）
        """
        if self._initialized:
            # 单例模式下，如果提供了新的 mcp_client 且当前 mcp_client 为 None，则更新它
            if mcp_client is not None and self._mcp_client is None:
                self._mcp_client = mcp_client
                logger.debug("Updated mcp_client in existing GUITools instance")
            return
        
        # 首次初始化
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._mcp_client = mcp_client
        self._use_mcp = False
        self._mcp_puppeteer_tools = {}  # 存储 MCP Puppeteer 工具名称映射
        self._initialized = True
        
        # 注意：MCP Puppeteer 检查会在首次使用时进行（因为此时 MCP 客户端可能还未连接）
    
    def get_name(self) -> str:
        return "gui_tools"
    
    def get_description(self) -> str:
        return "GUI操作工具集合，包括点击、输入、滚动、截图等操作"
    
    def _check_mcp_puppeteer(self) -> None:
        """检查是否可以使用 MCP Puppeteer 工具"""
        if not self._mcp_client or not self._mcp_client.connected:
            return
        
        try:
            # 获取 MCP 工具列表
            mcp_tools = self._mcp_client.get_tools()
            
            # 查找 Puppeteer 相关工具
            puppeteer_tool_names = {
                "navigate": ["navigate", "goto", "go_to", "navigate_to"],
                "click": ["click", "click_element"],
                "input": ["input", "type", "fill", "type_text"],
                "screenshot": ["screenshot", "capture_screenshot"],
                "scroll": ["scroll", "scroll_page"],
                "wait": ["wait", "wait_for", "wait_for_selector"]
            }
            
            # 检查是否有 Puppeteer 工具
            for tool in mcp_tools:
                tool_name = tool.get("name", "").lower()
                # 检查是否是 Puppeteer 工具（通常包含 puppeteer 或 browser 关键字）
                if "puppeteer" in tool_name or "browser" in tool_name:
                    # 尝试匹配工具名称
                    for action, possible_names in puppeteer_tool_names.items():
                        if any(name in tool_name for name in possible_names):
                            self._mcp_puppeteer_tools[action] = tool.get("name")
                            logger.debug(f"Found MCP Puppeteer tool for {action}: {tool.get('name')}")
            
            # 如果找到了至少一个 Puppeteer 工具，启用 MCP 模式
            if self._mcp_puppeteer_tools:
                self._use_mcp = True
                logger.info(f"Using MCP Puppeteer for browser control. Found {len(self._mcp_puppeteer_tools)} tools.")
            else:
                logger.debug("No MCP Puppeteer tools found, will use Playwright")
        
        except Exception as e:
            logger.warning(f"Error checking MCP Puppeteer tools: {e}")
            self._use_mcp = False
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用 MCP Puppeteer 工具"""
        if not self._mcp_client or not self._mcp_client.connected:
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self._mcp_client.call_tool(tool_name, arguments)
            
            # 处理 MCP 返回结果
            if isinstance(result, dict):
                if result.get("isError"):
                    error_msg = result.get("error", "Unknown error")
                    return {
                        "success": False,
                        "error": error_msg,
                        "message": f"MCP tool error: {error_msg}"
                    }
                
                # 提取文本内容
                if "text" in result:
                    return {
                        "success": True,
                        "data": result.get("text"),
                        "message": "MCP tool executed successfully"
                    }
                elif "content" in result and result["content"]:
                    first_content = result["content"][0]
                    if isinstance(first_content, dict):
                        text = first_content.get("text", "")
                        return {
                            "success": True,
                            "data": text,
                            "message": "MCP tool executed successfully"
                        }
                
                return {
                    "success": True,
                    "data": result,
                    "message": "MCP tool executed successfully"
                }
            
            return {
                "success": True,
                "data": result,
                "message": "MCP tool executed successfully"
            }
        
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise
    
    async def _ensure_browser(self) -> None:
        """确保浏览器已启动（仅在使用 Playwright 时）"""
        # 如果使用 MCP Puppeteer，不需要启动 Playwright 浏览器
        if self._use_mcp:
            return
        
        if self._browser is None:
            self._playwright = await async_playwright().start()
            # 启动浏览器，优化启动速度
            # slow_mo设置为0以提高速度，只在必要时添加延迟
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                slow_mo=0  # 移除延迟以提高速度
            )
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
            logger.info("Browser started")
    
    async def _get_page(self) -> Page:
        """获取当前页面（仅在使用 Playwright 时）"""
        # 如果使用 MCP Puppeteer，不需要获取 Playwright 页面
        if self._use_mcp:
            raise RuntimeError("Cannot get Playwright page when using MCP Puppeteer")
        
        await self._ensure_browser()
        if self._page is None:
            self._page = await self._context.new_page()
        return self._page
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行GUI操作
        
        Args:
            args: 操作参数，格式：
                {
                    "action": "click|input|scroll|screenshot|wait|navigate",
                    "target": "选择器或坐标",
                    "value": "输入值（可选）",
                    "url": "URL（navigate时使用）"
                }
        """
        action = args.get("action")
        
        try:
            if action == "navigate":
                return await self._navigate(args)
            elif action == "click":
                return await self._click(args)
            elif action == "input":
                return await self._input(args)
            elif action == "scroll":
                return await self._scroll(args)
            elif action == "screenshot":
                return await self._screenshot(args)
            elif action == "wait":
                return await self._wait(args)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "message": f"未知操作: {action}"
                }
        except Exception as e:
            logger.error(f"GUI action error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"GUI操作失败: {str(e)}"
            }
    
    async def _navigate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """导航到URL"""
        url = args.get("url")
        if not url:
            return {
                "success": False,
                "error": "URL is required",
                "message": "需要提供URL"
            }
        
        # 检查是否可以使用 MCP Puppeteer（如果之前没有检查过）
        if self._mcp_client and not self._mcp_puppeteer_tools:
            self._check_mcp_puppeteer()
        
        # 如果使用 MCP Puppeteer
        if self._use_mcp and "navigate" in self._mcp_puppeteer_tools:
            tool_name = self._mcp_puppeteer_tools["navigate"]
            try:
                result = await self._call_mcp_tool(tool_name, {"url": url})
                if result.get("success"):
                    return {
                        "success": True,
                        "data": {"url": url},
                        "message": f"已通过MCP导航到 {url}"
                    }
            except Exception as e:
                logger.warning(f"MCP navigate failed, falling back to Playwright: {e}")
                # 回退到 Playwright
        
        # 使用 Playwright
        page = await self._get_page()
        await page.goto(url)
        return {
            "success": True,
            "data": {"url": url},
            "message": f"已导航到 {url}"
        }
    
    async def _click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """点击元素"""
        target = args.get("target")
        if not target:
            return {
                "success": False,
                "error": "Target is required",
                "message": "需要提供目标元素"
            }
        
        # 检查是否可以使用 MCP Puppeteer（如果之前没有检查过）
        if self._mcp_client and not self._mcp_puppeteer_tools:
            self._check_mcp_puppeteer()
        
        # 如果使用 MCP Puppeteer
        if self._use_mcp and "click" in self._mcp_puppeteer_tools:
            tool_name = self._mcp_puppeteer_tools["click"]
            try:
                result = await self._call_mcp_tool(tool_name, {"selector": target})
                if result.get("success"):
                    return {
                        "success": True,
                        "data": {"target": target},
                        "message": f"已通过MCP点击 {target}"
                    }
            except Exception as e:
                logger.warning(f"MCP click failed, falling back to Playwright: {e}")
                # 回退到 Playwright
        
        # 使用 Playwright
        page = await self._get_page()
        
        try:
            # 等待元素可见和可点击
            await page.wait_for_selector(target, state="visible", timeout=5000)
            await page.click(target, timeout=5000)
            
            return {
                "success": True,
                "data": {"target": target},
                "message": f"已点击 {target}"
            }
        except Exception as e:
            logger.error(f"Click error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"点击失败: {str(e)}"
            }
    
    async def _input(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """输入文本"""
        target = args.get("target")
        value = args.get("value", "")
        
        if not target:
            return {
                "success": False,
                "error": "Target is required",
                "message": "需要提供目标元素"
            }
        
        # 检查是否可以使用 MCP Puppeteer（如果之前没有检查过）
        if self._mcp_client and not self._mcp_puppeteer_tools:
            self._check_mcp_puppeteer()
        
        # 如果使用 MCP Puppeteer
        if self._use_mcp and "input" in self._mcp_puppeteer_tools:
            tool_name = self._mcp_puppeteer_tools["input"]
            try:
                result = await self._call_mcp_tool(tool_name, {"selector": target, "text": value})
                if result.get("success"):
                    return {
                        "success": True,
                        "data": {"target": target, "value": value},
                        "message": f"已通过MCP输入文本到 {target}"
                    }
            except Exception as e:
                logger.warning(f"MCP input failed, falling back to Playwright: {e}")
                # 回退到 Playwright
        
        # 使用 Playwright
        page = await self._get_page()
        
        try:
            # 等待元素可见
            await page.wait_for_selector(target, state="visible", timeout=5000)
            
            # 先点击元素确保获得焦点
            await page.click(target)
            await page.wait_for_timeout(100)  # 短暂等待
            
            # 清空现有内容
            await page.fill(target, "")
            
            # 使用type方法输入，更可靠
            await page.type(target, value, delay=50)  # 模拟真实输入，每个字符延迟50ms
            
            # 验证输入是否成功
            input_value = await page.input_value(target)
            if value in input_value or input_value == value:
                return {
                    "success": True,
                    "data": {"target": target, "value": value},
                    "message": f"已输入文本到 {target}"
                }
            else:
                return {
                    "success": False,
                    "error": "Input verification failed",
                    "message": f"输入验证失败，期望: {value}, 实际: {input_value}"
                }
        
        except Exception as e:
            logger.error(f"Input error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"输入失败: {str(e)}"
            }
    
    async def _scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """滚动页面"""
        direction = args.get("direction", "down")  # up, down
        amount = args.get("amount", 500)
        
        page = await self._get_page()
        if direction == "down":
            await page.evaluate(f"window.scrollBy(0, {amount})")
        else:
            await page.evaluate(f"window.scrollBy(0, -{amount})")
        
        return {
            "success": True,
            "data": {"direction": direction, "amount": amount},
            "message": f"已向{direction}滚动{amount}px"
        }
    
    async def _screenshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """截图"""
        path = args.get("path", "screenshot.png")
        full_page = args.get("full_page", False)
        
        # 检查是否可以使用 MCP Puppeteer（如果之前没有检查过）
        if self._mcp_client and not self._mcp_puppeteer_tools:
            self._check_mcp_puppeteer()
        
        # 如果使用 MCP Puppeteer
        if self._use_mcp and "screenshot" in self._mcp_puppeteer_tools:
            tool_name = self._mcp_puppeteer_tools["screenshot"]
            try:
                result = await self._call_mcp_tool(tool_name, {"path": path, "fullPage": full_page})
                if result.get("success"):
                    return {
                        "success": True,
                        "data": {"path": path},
                        "message": f"已通过MCP截图保存到 {path}"
                    }
            except Exception as e:
                logger.warning(f"MCP screenshot failed, falling back to Playwright: {e}")
                # 回退到 Playwright
        
        # 使用 Playwright
        page = await self._get_page()
        await page.screenshot(path=path, full_page=full_page)
        
        return {
            "success": True,
            "data": {"path": path},
            "message": f"截图已保存到 {path}"
        }
    
    async def _wait(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """等待"""
        timeout = args.get("timeout", 1000)  # 毫秒
        selector = args.get("selector")  # 可选：等待元素出现
        
        page = await self._get_page()
        if selector:
            await page.wait_for_selector(selector, timeout=timeout)
        else:
            await page.wait_for_timeout(timeout)
        
        return {
            "success": True,
            "data": {"timeout": timeout},
            "message": "等待完成"
        }
    
    async def close(self) -> None:
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")


# 创建独立的工具实例（每个操作一个工具类，便于注册）
# 注意：这些工具需要能够访问 MCP 客户端，但当前设计是单例模式
# 如果需要 MCP 支持，需要在初始化时传入 MCP 客户端
class NavigateTool(BaseTool):
    """导航工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "navigate"
    
    def get_description(self) -> str:
        return "navigate - 在浏览器中导航到指定URL"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "navigate", **args})


class ClickTool(BaseTool):
    """点击工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "click"
    
    def get_description(self) -> str:
        return "click - 点击页面上的元素（通过CSS选择器）"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "click", **args})


class InputTool(BaseTool):
    """输入工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "input"
    
    def get_description(self) -> str:
        return "input - 在输入框中输入文本"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "input", **args})


class ScrollTool(BaseTool):
    """滚动工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "scroll"
    
    def get_description(self) -> str:
        return "scroll - 滚动页面（向上或向下）"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "scroll", **args})


class ScreenshotTool(BaseTool):
    """截图工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "screenshot"
    
    def get_description(self) -> str:
        return "screenshot - 截取当前页面截图"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "screenshot", **args})


class WaitTool(BaseTool):
    """等待工具"""
    
    def __init__(self, mcp_client=None):
        super().__init__()
        self._mcp_client = mcp_client
    
    def get_name(self) -> str:
        return "wait"
    
    def get_description(self) -> str:
        return "wait - 等待指定时间或等待元素出现"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gui_tools = GUITools(mcp_client=self._mcp_client)
        return await gui_tools.execute({"action": "wait", **args})


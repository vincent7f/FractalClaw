"""
浏览器控制工具

基于 Playwright 实现浏览器自动化控制
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from fractalclaw.core.component import Component, LeafComponent, ComponentState


class BrowserType(Enum):
    """浏览器类型"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class BrowserAction(Enum):
    """浏览器动作"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    EVALUATE = "evaluate"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    WAIT_FOR_NAVIGATION = "wait_for_navigation"
    GET_ATTRIBUTE = "get_attribute"
    GET_TEXT = "get_text"


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    slow_mo: int = 0  # 慢动作延迟（毫秒）
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    user_agent: str = ""
    proxies: Optional[Dict[str, str]] = None
    timeout: int = 30000


@dataclass
class ActionResult:
    """动作结果"""
    success: bool
    data: Any = None
    error: str = ""


class BrowserController(LeafComponent):
    """
    浏览器控制器
    
    提供浏览器自动化操作能力
    """

    def __init__(
        self,
        name: str = "browser",
        config: Optional[BrowserConfig] = None,
    ):
        super().__init__(name)
        self.config = config or BrowserConfig()
        
        self._browser = None
        self._context = None
        self._page = None

    # ==================== 生命周期 ====================

    def _on_initialize(self):
        """初始化浏览器"""
        pass

    async def _on_start(self):
        """启动浏览器"""
        await self.launch()

    async def _on_stop(self):
        """关闭浏览器"""
        await self.close()

    # ==================== 浏览器操作 ====================

    async def launch(self) -> bool:
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            
            pw = await async_playwright().start()
            
            browser_type = self.config.browser_type.value
            browser = await getattr(pw, browser_type).launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo,
            )
            
            self._browser = browser
            self._playwright = pw
            
            # 创建默认上下文
            await self.new_context()
            
            return True
            
        except Exception as e:
            print(f"Failed to launch browser: {e}")
            return False

    async def new_context(self) -> Optional[Any]:
        """创建新上下文"""
        if not self._browser:
            return None
        
        self._context = await self._browser.new_context(
            viewport=self.config.viewport,
            user_agent=self.config.user_agent or None,
        )
        
        self._page = await self._context.new_page()
        return self._context

    async def new_page(self) -> Optional[Any]:
        """创建新页面"""
        if not self._context:
            await self.new_context()
        
        return await self._context.new_page()

    async def close(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()

    # ==================== 页面操作 ====================

    async def navigate(self, url: str, wait_until: str = "load") -> ActionResult:
        """导航到 URL"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            await self._page.goto(url, wait_until=wait_until, timeout=self.config.timeout)
            return ActionResult(success=True, data={"url": url})
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def click(self, selector: str) -> ActionResult:
        """点击元素"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            await self._page.click(selector, timeout=self.config.timeout)
            return ActionResult(success=True)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 0,
    ) -> ActionResult:
        """输入文本"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            await self._page.fill(selector, text)
            if delay > 0:
                await asyncio.sleep(delay / 1000)
            return ActionResult(success=True)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
    ) -> ActionResult:
        """截图"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            if path:
                await self._page.screenshot(path=path, full_page=full_page)
                return ActionResult(success=True, data={"path": path})
            else:
                data = await self._page.screenshot(full_page=full_page)
                import base64
                return ActionResult(success=True, data={"base64": base64.b64encode(data).decode()})
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def evaluate(self, script: str) -> ActionResult:
        """执行 JavaScript"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            result = await self._page.evaluate(script)
            return ActionResult(success=True, data=result)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """等待元素出现"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            await self._page.wait_for_selector(
                selector,
                timeout=timeout or self.config.timeout,
            )
            return ActionResult(success=True)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def wait_for_navigation(
        self,
        timeout: Optional[int] = None,
    ) -> ActionResult:
        """等待导航完成"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            await self._page.wait_for_load_state(
                "networkidle",
                timeout=timeout or self.config.timeout,
            )
            return ActionResult(success=True)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> ActionResult:
        """获取元素属性"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            value = await self._page.get_attribute(selector, attribute)
            return ActionResult(success=True, data=value)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def get_text(self, selector: str) -> ActionResult:
        """获取元素文本"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            text = await self._page.text_content(selector)
            return ActionResult(success=True, data=text)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    async def get_html(self, selector: Optional[str] = None) -> ActionResult:
        """获取 HTML"""
        if not self._page:
            return ActionResult(success=False, error="No page available")
        
        try:
            if selector:
                html = await self._page.inner_html(selector)
            else:
                html = await self._page.content()
            return ActionResult(success=True, data=html)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ==================== 高级操作 ====================

    async def execute_action(
        self,
        action: BrowserAction,
        params: Dict[str, Any],
    ) -> ActionResult:
        """执行动作"""
        action_enum = BrowserAction(action) if isinstance(action, str) else action
        
        if action_enum == BrowserAction.NAVIGATE:
            return await self.navigate(
                params.get("url", ""),
                params.get("wait_until", "load"),
            )
        elif action_enum == BrowserAction.CLICK:
            return await self.click(params.get("selector", ""))
        elif action_enum == BrowserAction.TYPE:
            return await self.type_text(
                params.get("selector", ""),
                params.get("text", ""),
                params.get("delay", 0),
            )
        elif action_enum == BrowserAction.SCREENSHOT:
            return await self.screenshot(
                params.get("path"),
                params.get("full_page", False),
            )
        elif action_enum == BrowserAction.EVALUATE:
            return await self.evaluate(params.get("script", ""))
        elif action_enum == BrowserAction.WAIT_FOR_SELECTOR:
            return await self.wait_for_selector(
                params.get("selector", ""),
                params.get("timeout"),
            )
        elif action_enum == BrowserAction.WAIT_FOR_NAVIGATION:
            return await self.wait_for_navigation(params.get("timeout"))
        elif action_enum == BrowserAction.GET_ATTRIBUTE:
            return await self.get_attribute(
                params.get("selector", ""),
                params.get("attribute", ""),
            )
        elif action_enum == BrowserAction.GET_TEXT:
            return await self.get_text(params.get("selector", ""))
        
        return ActionResult(success=False, error=f"Unknown action: {action}")

    # ==================== 工具方法 ====================

    def get_page(self):
        """获取当前页面"""
        return self._page

    def get_context(self):
        """获取当前上下文"""
        return self._context

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """获取 cookies"""
        if not self._context:
            return []
        return await self._context.cookies()

    async def set_cookies(self, cookies: List[Dict[str, Any]]):
        """设置 cookies"""
        if self._context:
            await self._context.add_cookies(cookies)

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class BrowserAction(str, Enum):
    NAVIGATE = "navigate"
    SNAPSHOT = "snapshot"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    EVALUATE = "evaluate"
    WAIT = "wait"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"
    CLOSE = "close"


class BrowserError(AicpError):
    pass


class BrowserTimeoutError(BrowserError):
    pass


class BrowserSecurityError(BrowserError):
    pass


@dataclass
class BrowserResult:
    url: Optional[str] = None
    title: Optional[str] = None
    snapshot: Optional[dict] = None
    screenshot: Optional[str] = None
    element_found: bool = False
    error: Optional[str] = None


class Viewport(BaseModel):
    width: int = 1920
    height: int = 1080


class BrowserConfig(BaseModel):
    action: BrowserAction
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    script: Optional[str] = None
    wait_for: Optional[str] = None
    headless: bool = True
    viewport: Viewport = Field(default_factory=Viewport)
    timeout_ms: int = 30000


PRIVATE_IP_PATTERNS = [
    "127.",
    "localhost",
    "0.0.0.0",
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.2",
    "172.30.",
    "172.31.",
    "192.168.",
    "169.254.",
    "::1",
    "fc00:",
    "fe80:",
]


def _is_private_url(url: str) -> bool:
    url_lower = url.lower()
    for pattern in PRIVATE_IP_PATTERNS:
        if pattern in url_lower:
            return True
    return False


class BrowserService:
    def __init__(self):
        self._contexts: dict[str, Any] = {}
        self._playwright = None
        self._browser = None

    async def _ensure_playwright(self) -> Any:
        if self._playwright is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
            except ImportError:
                raise BrowserError(
                    "Playwright not installed. Run: pip install playwright && playwright install chromium"
                )
        return self._playwright

    async def _ensure_browser(self) -> Any:
        pw = await self._ensure_playwright()
        if self._browser is None:
            self._browser = await pw.chromium.launch(headless=True)
        return self._browser

    async def create_context(
        self,
        session_id: str,
        headless: bool = True,
        viewport: Optional[Viewport] = None,
    ) -> str:
        browser = await self._ensure_browser()
        vp = viewport or Viewport()
        context = await browser.new_context(
            viewport={"width": vp.width, "height": vp.height},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        self._contexts[session_id] = {
            "context": context,
            "page": page,
            "headless": headless,
        }
        return session_id

    async def navigate(self, session_id: str, url: str) -> BrowserResult:
        if _is_private_url(url):
            raise BrowserSecurityError(f"Navigation to private IP blocked: {url}")
        if session_id not in self._contexts:
            await self.create_context(session_id)
        page = self._contexts[session_id]["page"]
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await page.title()
            return BrowserResult(
                url=page.url,
                title=title,
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=str(e))

    async def snapshot(self, session_id: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            a11y = await page.accessibility.snapshot()
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                snapshot=a11y,
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=str(e))

    async def click(self, session_id: str, selector: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            await page.click(selector, timeout=10000)
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=f"Element not found: {selector} - {str(e)}")

    async def type_text(
        self, session_id: str, selector: str, text: str
    ) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            await page.fill(selector, text, timeout=10000)
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=f"Element not found: {selector} - {str(e)}")

    async def screenshot(self, session_id: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            img = await page.screenshot()
            import base64

            b64 = base64.b64encode(img).decode()
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                screenshot=b64,
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=str(e))

    async def evaluate(self, session_id: str, script: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            result = await page.evaluate(script)
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                snapshot=result,
                element_found=True,
            )
        except Exception as e:
            return BrowserResult(error=str(e))

    async def wait_for(
        self, session_id: str, selector: str, timeout_ms: int = 10000
    ) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
            return BrowserResult(
                url=page.url,
                title=await page.title(),
                element_found=True,
            )
        except Exception:
            return BrowserResult(error=f"Timeout waiting for: {selector}")

    async def back(self, session_id: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        await page.go_back()
        return BrowserResult(url=page.url, title=await page.title(), element_found=True)

    async def forward(self, session_id: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        await page.go_forward()
        return BrowserResult(url=page.url, title=await page.title(), element_found=True)

    async def refresh(self, session_id: str) -> BrowserResult:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        page = self._contexts[session_id]["page"]
        await page.reload()
        return BrowserResult(url=page.url, title=await page.title(), element_found=True)

    async def close_context(self, session_id: str) -> None:
        if session_id in self._contexts:
            await self._contexts[session_id]["context"].close()
            del self._contexts[session_id]

    async def get_cookies(self, session_id: str) -> list[dict]:
        if session_id not in self._contexts:
            return []
        return await self._contexts[session_id]["context"].cookies()

    async def set_cookies(self, session_id: str, cookies: list[dict]) -> None:
        if session_id not in self._contexts:
            raise BrowserError(f"No context for session: {session_id}")
        await self._contexts[session_id]["context"].add_cookies(cookies)

    async def close(self) -> None:
        for session_id in list(self._contexts.keys()):
            await self.close_context(session_id)
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

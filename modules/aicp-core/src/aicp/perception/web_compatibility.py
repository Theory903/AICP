import asyncio
from abc import ABC, abstractmethod
from typing import Any

from playwright.async_api import Browser, Page, ViewportSize, async_playwright
from pydantic import BaseModel


class WebCompatibilityConfig(BaseModel):
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    viewport: ViewportSize = {"width": 1280, "height": 800}
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    locale: str = "en-US"
    timezone_id: str = "UTC"

class HumanWebCompatibilityProvider(ABC):
    @abstractmethod
    async def get_compatible_page(self, url: str) -> Any:
        pass

    @abstractmethod
    async def inject_human_patterns(self, page: Any) -> None:
        pass

class PlaywrightWebCompatibilityProvider(HumanWebCompatibilityProvider):
    def __init__(self, config: WebCompatibilityConfig | None = None, headless: bool = True):
        self.config = config or WebCompatibilityConfig()
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None

    async def _ensure_browser(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def get_compatible_page(self, url: str) -> Page:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")

        context = await self._browser.new_context(
            user_agent=self.config.user_agent,
            viewport=self.config.viewport,
            device_scale_factor=self.config.device_scale_factor,
            is_mobile=self.config.is_mobile,
            has_touch=self.config.has_touch,
            locale=self.config.locale,
            timezone_id=self.config.timezone_id
        )
        page = await context.new_page()
        await self.inject_human_patterns(page)
        await page.goto(url, wait_until="networkidle")
        return page

    async def inject_human_patterns(self, page: Page) -> None:
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

    async def human_click(self, page: Page, selector: str):
        element = await page.wait_for_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                import random
                x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                await page.mouse.move(x, y, steps=10)
                await page.mouse.click(x, y)

    async def human_type(self, page: Page, selector: str, text: str):
        import random
        await page.focus(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

import pytest
from aicp_runtime.services.browser import (
    BrowserAction,
    BrowserConfig,
    BrowserError,
    BrowserSecurityError,
    BrowserService,
    Viewport,
    _is_private_url,
)


class TestBrowserConfig:
    def test_default_config(self):
        config = BrowserConfig(action=BrowserAction.NAVIGATE)
        assert config.action == BrowserAction.NAVIGATE
        assert config.headless is True
        assert config.viewport.width == 1920
        assert config.viewport.height == 1080
        assert config.timeout_ms == 30000

    def test_custom_viewport(self):
        config = BrowserConfig(
            action=BrowserAction.NAVIGATE,
            viewport=Viewport(width=1280, height=720),
        )
        assert config.viewport.width == 1280
        assert config.viewport.height == 720

    def test_config_validation(self):
        config = BrowserConfig(
            action=BrowserAction.CLICK,
            selector="#button",
            wait_for=".loaded",
        )
        assert config.selector == "#button"
        assert config.wait_for == ".loaded"


class TestBrowserSecurity:
    def test_blocks_private_ip_127(self):
        assert _is_private_url("http://127.0.0.1/admin") is True

    def test_blocks_private_ip_10(self):
        assert _is_private_url("http://10.0.0.1/api") is True

    def test_blocks_localhost(self):
        assert _is_private_url("http://localhost:8080") is True

    def test_blocks_192_168(self):
        assert _is_private_url("http://192.168.1.1") is True

    def test_allows_public_url(self):
        assert _is_private_url("https://example.com") is False

    def test_allows_public_url_with_path(self):
        assert _is_private_url("https://api.github.com/users") is False


@pytest.mark.asyncio
class TestBrowserService:
    async def test_create_context(self):
        service = BrowserService()
        session_id = await service.create_context("test-session", headless=True)
        assert session_id == "test-session"
        assert "test-session" in service._contexts
        await service.close()

    async def test_create_context_with_viewport(self):
        service = BrowserService()
        session_id = await service.create_context(
            "test-session",
            viewport=Viewport(width=800, height=600),
        )
        assert session_id == "test-session"
        await service.close()

    async def test_navigate_creates_context_if_missing(self):
        service = BrowserService()
        await service.navigate("new-session", "https://example.com")
        assert "new-session" in service._contexts
        await service.close()

    async def test_navigate_blocks_private_url(self):
        service = BrowserService()
        with pytest.raises(BrowserSecurityError):
            await service.navigate("test", "http://127.0.0.1/secret")
        await service.close()

    async def test_navigate_blocks_localhost(self):
        service = BrowserService()
        with pytest.raises(BrowserSecurityError):
            await service.navigate("test", "http://localhost:3000")
        await service.close()

    async def test_snapshot_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.snapshot("nonexistent")
        await service.close()

    async def test_click_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.click("nonexistent", "#btn")
        await service.close()

    async def test_type_text_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.type_text("nonexistent", "#input", "text")
        await service.close()

    async def test_screenshot_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.screenshot("nonexistent")
        await service.close()

    async def test_evaluate_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.evaluate("nonexistent", "1+1")
        await service.close()

    async def test_wait_for_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.wait_for("nonexistent", "#element")
        await service.close()

    async def test_back_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.back("nonexistent")
        await service.close()

    async def test_forward_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.forward("nonexistent")
        await service.close()

    async def test_refresh_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.refresh("nonexistent")
        await service.close()

    async def test_close_context_removes_session(self):
        service = BrowserService()
        await service.create_context("to-close")
        assert "to-close" in service._contexts
        await service.close_context("to-close")
        assert "to-close" not in service._contexts
        await service.close()

    async def test_get_cookies_returns_empty_for_missing_session(self):
        service = BrowserService()
        cookies = await service.get_cookies("nonexistent")
        assert cookies == []
        await service.close()

    async def test_set_cookies_requires_context(self):
        service = BrowserService()
        with pytest.raises(BrowserError):
            await service.set_cookies("nonexistent", [])
        await service.close()

    async def test_close_cleans_up_all_contexts(self):
        service = BrowserService()
        await service.create_context("session1")
        await service.create_context("session2")
        await service.close()
        assert len(service._contexts) == 0
        assert service._browser is None
        assert service._playwright is None


class TestViewport:
    def test_default_dimensions(self):
        vp = Viewport()
        assert vp.width == 1920
        assert vp.height == 1080

    def test_custom_dimensions(self):
        vp = Viewport(width=1024, height=768)
        assert vp.width == 1024
        assert vp.height == 768


class TestBrowserActions:
    def test_action_enum_values(self):
        assert BrowserAction.NAVIGATE == "navigate"
        assert BrowserAction.SNAPSHOT == "snapshot"
        assert BrowserAction.CLICK == "click"
        assert BrowserAction.TYPE == "type"
        assert BrowserAction.SCREENSHOT == "screenshot"
        assert BrowserAction.EVALUATE == "evaluate"
        assert BrowserAction.WAIT == "wait"
        assert BrowserAction.BACK == "back"
        assert BrowserAction.FORWARD == "forward"
        assert BrowserAction.REFRESH == "refresh"
        assert BrowserAction.CLOSE == "close"

import asyncio
from typing import Any

from playwright.async_api import Browser, async_playwright

from .perception import (
    A11yElement,
    AccessibilityTree,
    DOMElement,
    DOMSnapshot,
    InteractionType,
    PerceptionProvider,
    UserInteraction,
)


class PlaywrightPerceptionProvider(PerceptionProvider):
    """
    Production-grade Playwright implementation of PerceptionProvider.
    Handles a11y tree extraction, DOM snapshots, and screenshots.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None

    async def _ensure_browser(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def get_accessibility_tree(self, url: str) -> AccessibilityTree:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")

            accessibility = getattr(page, "accessibility", None)
            try:
                snapshot = await accessibility.snapshot() if accessibility else None
            except (AttributeError, TypeError):
                session = await context.new_cdp_session(page)
                ax_tree = await session.send("Accessibility.getFullAXTree")
                nodes = {node["nodeId"]: node for node in ax_tree.get("nodes", [])}

                def serialize(node_id: str) -> dict[str, Any]:
                    node = nodes[node_id]
                    role = node.get("role", {}).get("value", "unknown")
                    if role == "RootWebArea":
                        role = "document"
                    return {
                        "role": role,
                        "name": node.get("name", {}).get("value"),
                        "children": [serialize(child_id) for child_id in node.get("childIds", []) if child_id in nodes],
                    }

                root_id = next(
                    (
                        node_id
                        for node_id, node in nodes.items()
                        if node.get("role", {}).get("value") == "RootWebArea"
                    ),
                    None,
                )
                snapshot = serialize(root_id) if root_id else await page.evaluate("""
                    () => {
                        const inferRole = (el) => {
                            const tag = el.tagName.toLowerCase();
                            const explicit = el.getAttribute('role');
                            if (explicit) return explicit;
                            if (tag === 'form') return 'form';
                            if (tag === 'dialog') return 'dialog';
                            if (
                                tag === 'button' ||
                                (tag === 'input' && ['button', 'submit', 'reset'].includes(el.type))
                            ) return 'button';
                            if (tag === 'input' || tag === 'textarea' || tag === 'select') return 'textbox';
                            return 'generic';
                        };
                        const serialize = (el) => ({
                            role: inferRole(el),
                            name: el.getAttribute('aria-label') || el.getAttribute('name') || el.id || '',
                            children: Array.from(el.children).map(serialize),
                        });
                        return {
                            role: 'document',
                            name: document.title || '',
                            children: Array.from(document.body.children).map(serialize),
                        };
                    }
                """)

            def has_role(node: Any, target: str) -> bool:
                if not isinstance(node, dict):
                    return False
                if node.get("role", "").lower() == target.lower():
                    return True
                return any(has_role(child, target) for child in node.get("children", []))

            if not has_role(snapshot, "form"):
                snapshot = await page.evaluate("""
                    () => {
                        const inferRole = (el) => {
                            const tag = el.tagName.toLowerCase();
                            const explicit = el.getAttribute('role');
                            if (explicit) return explicit;
                            if (tag === 'form') return 'form';
                            if (tag === 'dialog') return 'dialog';
                            if (
                                tag === 'button' ||
                                (tag === 'input' && ['button', 'submit', 'reset'].includes(el.type))
                            ) return 'button';
                            if (tag === 'input' || tag === 'textarea' || tag === 'select') return 'textbox';
                            return 'generic';
                        };
                        const serialize = (el) => ({
                            role: inferRole(el),
                            name: el.getAttribute('aria-label') || el.getAttribute('name') || el.id || '',
                            children: Array.from(el.children).map(serialize),
                        });
                        return {
                            role: 'document',
                            name: document.title || '',
                            children: Array.from(document.body.children).map(serialize),
                        };
                    }
                """)

            if not snapshot:
                raise ValueError(f"Failed to capture accessibility snapshot for {url}")

            root_element = self._map_a11y_node(snapshot)

            tree = AccessibilityTree(
                url=url,
                title=await page.title(),
                root=root_element,
                element_count=self._count_nodes(root_element)
            )
            return tree
        finally:
            await page.close()
            await context.close()

    def _map_a11y_node(self, node: dict[str, Any], parent_id: str | None = None) -> A11yElement:
        children = []
        if "children" in node:
            for child in node["children"]:
                children.append(self._map_a11y_node(child, parent_id=None))

        element = A11yElement(
            role=node.get("role", "unknown"),
            name=node.get("name"),
            value=str(node.get("value")) if node.get("value") is not None else None,
            description=node.get("description"),
            disabled=node.get("disabled", False),
            focused=node.get("focused", False),
            checked=node.get("checked"),
            expanded=node.get("expanded"),
            parent_id=parent_id,
            children=children
        )

        for child in element.children:
            child.parent_id = element.id

        return element

    def _count_nodes(self, element: A11yElement) -> int:
        count = 1
        for child in element.children:
            count += self._count_nodes(child)
        return count

    async def get_dom_snapshot(self, url: str) -> DOMSnapshot:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")

            dom_data = await page.evaluate("""
                () => {
                    const serialize = (el) => {
                        return {
                            id: el.id || `node_${Math.random().toString(36).substr(2, 9)}`,
                            tag: el.tagName.toLowerCase(),
                            attributes: Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value])),
                            text_content: el.children.length === 0 ? el.textContent.trim() : null,
                            children: Array.from(el.children).map(serialize)
                        };
                    };
                    return serialize(document.body);
                }
            """)

            root = self._map_dom_node(dom_data)

            forms = await page.evaluate(
                "() => Array.from(document.forms).map(f => ({ id: f.id, action: f.action }))"
            )
            inputs = await page.evaluate(
                "() => Array.from(document.querySelectorAll('input, select, textarea'))"
                ".map(i => ({ id: i.id, type: i.type, name: i.name }))"
            )

            return DOMSnapshot(
                url=url,
                root=root,
                title=await page.title(),
                forms=forms,
                inputs=inputs
            )
        finally:
            await page.close()
            await context.close()

    def _map_dom_node(self, data: dict[str, Any]) -> DOMElement:
        children = [self._map_dom_node(c) for c in data.get("children", [])]
        return DOMElement(
            id=data["id"],
            tag=data["tag"],
            attributes=data.get("attributes", {}),
            text_content=data.get("text_content"),
            children=children
        )

    async def capture_screenshot(self, url: str, element_id: str | None = None) -> bytes:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            if element_id:
                element = await page.query_selector(f"#{element_id}")
                if element:
                    return await element.screenshot()
            return await page.screenshot(full_page=True)
        finally:
            await page.close()
            await context.close()

    async def observe_interactions(self, url: str) -> list[UserInteraction]:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")

            interactions: list[UserInteraction] = []

            await page.expose_function("onInteraction", lambda i: interactions.append(UserInteraction(**i)))

            await page.add_init_script("""
                window.addEventListener('click', (e) => {
                    window.onInteraction({
                        type: 'click',
                        target_id: e.target.id || e.target.tagName,
                        timestamp: new Date().toISOString(),
                        metadata: { x: e.clientX, y: e.clientY }
                    });
                });
                window.addEventListener('input', (e) => {
                    window.onInteraction({
                        type: 'input',
                        target_id: e.target.id || e.target.name,
                        value: e.target.value,
                        timestamp: new Date().toISOString()
                    });
                });
            """)

            await asyncio.sleep(5.0)

            return interactions
        finally:
            await page.close()
            await context.close()

    async def execute_action(
        self,
        url: str,
        action_type: InteractionType,
        target_id: str,
        value: str | None = None,
    ) -> bool:
        await self._ensure_browser()
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        context = await self._browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")

            selector = f"#{target_id}" if not target_id.startswith((".", "[")) else target_id

            if action_type == InteractionType.CLICK:
                await page.click(selector)
            elif action_type == InteractionType.TYPE:
                await page.fill(selector, value or "")
            elif action_type == InteractionType.HOVER:
                await page.hover(selector)
            elif action_type == InteractionType.SELECT:
                await page.select_option(selector, value)

            return True
        except Exception as e:
            print(f"Browser action failed: {e}")
            return False
        finally:
            await page.close()
            await context.close()

    async def stop(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

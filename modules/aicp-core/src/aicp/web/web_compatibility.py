"""Human Web Compatibility - Module 17"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InteractionTarget(str, Enum):
    ELEMENT_ID = "element_id"
    CSS_SELECTOR = "css_selector"
    XPATH = "xpath"
    ACCESSIBILITY_ROLE = "accessibility_role"
    TEXT = "text"
    LABEL = "label"


class WebActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    SUBMIT = "submit"
    HOVER = "hover"
    SCROLL = "scroll"
    WAIT = "wait"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    WAIT_FOR_NAVIGATION = "wait_for_navigation"
    WAIT_FOR_TEXT = "wait_for_text"
    SCREENSHOT = "screenshot"
    EVALUATE = "evaluate"


class WebAction(BaseModel):
    id: str = Field(default_factory=lambda: f"webact_{uuid.uuid4().hex[:8]}")
    action_type: WebActionType
    target: str | None = None
    target_type: InteractionTarget = InteractionTarget.CSS_SELECTOR
    value: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = 30000
    description: str | None = None


class WebInteraction(BaseModel):
    id: str = Field(default_factory=lambda: f"webint_{uuid.uuid4().hex[:8]}")
    url: str
    actions: list[WebAction]
    viewport: dict[str, int] | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FormField(BaseModel):
    name: str
    field_type: str
    label: str | None = None
    selector: str | None = None
    xpath: str | None = None
    a11y_role: str | None = None
    required: bool = False
    pattern: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    options: list[dict[str, str]] = Field(default_factory=list)


class FormDefinition(BaseModel):
    id: str = Field(default_factory=lambda: f"form_{uuid.uuid4().hex[:8]}")
    url_pattern: str
    name: str
    fields: list[FormField]
    submit_button_selector: str | None = None
    submit_strategy: str = "click"
    success_indicators: list[str] = Field(default_factory=list)
    error_indicators: list[str] = Field(default_factory=list)


class PageState(BaseModel):
    url: str
    title: str | None = None
    accessibility_tree: dict[str, Any] | None = None
    dom_snapshot: dict[str, Any] | None = None
    visible_text: str | None = None
    forms: list[FormDefinition] = Field(default_factory=list)
    interactive_elements: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WebAutomationProvider(ABC):

    @abstractmethod
    async def navigate(self, url: str, wait_until: str = "networkidle") -> PageState:
        pass

    @abstractmethod
    async def perform_action(self, action: WebAction) -> dict[str, Any]:
        pass

    @abstractmethod
    async def execute_interaction(self, interaction: WebInteraction) -> dict[str, Any]:
        pass

    @abstractmethod
    async def fill_form(self, form: FormDefinition, data: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_page_state(self) -> PageState:
        pass

    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout_ms: int = 30000) -> bool:
        pass

    @abstractmethod
    async def wait_for_text(self, text: str, timeout_ms: int = 30000) -> bool:
        pass


class WebInteractionService:
    def __init__(self, provider: WebAutomationProvider | None = None):
        self._provider = provider
        self._form_registry: dict[str, FormDefinition] = {}
        self._interaction_history: list[WebInteraction] = []

    def register_form(self, form: FormDefinition) -> None:
        self._form_registry[form.id] = form

    def get_form(self, url_pattern: str) -> FormDefinition | None:
        for form in self._form_registry.values():
            if form.url_pattern in url_pattern:
                return form
        return None

    async def fill_and_submit(self, url: str, form_data: dict[str, Any]) -> dict[str, Any]:
        form = self.get_form(url)
        if not form:
            return {"status": "error", "message": f"No form found for {url}"}

        if not self._provider:
            return {"status": "error", "message": "No web automation provider configured"}

        return await self._provider.fill_form(form, form_data)

    async def execute_workflow(self, interaction: WebInteraction) -> dict[str, Any]:
        if not self._provider:
            return {"status": "error", "message": "No web automation provider configured"}

        result = await self._provider.execute_interaction(interaction)
        self._interaction_history.append(interaction)
        return result

    def get_history(self, limit: int = 50) -> list[WebInteraction]:
        return self._interaction_history[-limit:]


class A11yWebBridge:
    def __init__(self, provider: WebAutomationProvider):
        self._provider = provider

    async def find_element_by_role(self, role: str, name: str | None = None) -> dict[str, Any] | None:
        state = await self._provider.get_page_state()
        if not state.accessibility_tree:
            return None

        return self._search_by_role(state.accessibility_tree, role, name)

    def _search_by_role(self, tree: dict[str, Any], role: str, name: str | None) -> dict[str, Any] | None:
        if tree.get("role") == role and (name is None or tree.get("name") == name):
            return tree

        for child in tree.get("children", []):
            result = self._search_by_role(child, role, name)
            if result:
                return result
        return None

    async def click_element_by_role(self, role: str, name: str | None = None) -> dict[str, Any]:
        element = await self.find_element_by_role(role, name)
        if not element:
            return {"status": "error", "message": f"No element found with role={role}, name={name}"}

        action = WebAction(
            action_type=WebActionType.CLICK,
            target=element.get("id"),
            target_type=InteractionTarget.ELEMENT_ID,
            description=f"Click {role}: {name}"
        )

        return await self._provider.perform_action(action)

    async def fill_field_by_label(self, label: str, value: str) -> dict[str, Any]:
        element = await self.find_element_by_role("textbox", label)
        if not element:
            element = await self.find_element_by_role("input", label)

        if not element:
            return {"status": "error", "message": f"No field found with label={label}"}

        action = WebAction(
            action_type=WebActionType.TYPE,
            target=element.get("id"),
            target_type=InteractionTarget.ELEMENT_ID,
            value=value,
            description=f"Fill {label}"
        )

        return await self._provider.perform_action(action)


class ScreenshotManager:
    def __init__(self, provider: WebAutomationProvider):
        self._provider = provider
        self._screenshots: list[dict[str, Any]] = []

    async def capture(self, name: str | None = None, full_page: bool = False) -> str:
        action = WebAction(
            action_type=WebActionType.SCREENSHOT,
            options={"fullPage": full_page},
            description=name or "screenshot"
        )

        result = await self._provider.perform_action(action)
        screenshot_data = result.get("data")

        if screenshot_data:
            self._screenshots.append({
                "id": f"screenshot_{uuid.uuid4().hex[:8]}",
                "name": name,
                "timestamp": datetime.utcnow().isoformat(),
                "data": screenshot_data,
                "full_page": full_page
            })

        return screenshot_data or ""

    def get_history(self) -> list[dict[str, Any]]:
        return self._screenshots

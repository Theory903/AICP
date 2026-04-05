"""
Perception and Signal Layer
Module 6 - a11y tree, DOM observation, screenshots, behavioral signals
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class SignalType(str, Enum):
    """Types of perception signals"""
    ACCESSIBILITY_TREE = "accessibility_tree"
    DOM_SNAPSHOT = "dom_snapshot"
    SCREENSHOT = "screenshot"
    USER_INTERACTION = "user_interaction"
    STATE_CHANGE = "state_change"
    ELEMENT_FOCUS = "element_focus"


class ElementRole(str, Enum):
    """Accessibility element roles"""
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    TEXTBOX = "textbox"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    COMBOBOX = "combobox"
    MENU = "menu"
    MENU_ITEM = "menuitem"
    TAB = "tab"
    TAB_PANEL = "tabpanel"
    DIALOG = "dialog"
    ALERT = "alert"
    FORM = "form"
    LANDMARK = "landmark"
    HEADING = "heading"
    IMAGE = "image"
    TEXT = "text"
    UNKNOWN = "unknown"


class A11yElement(BaseModel):
    """Accessibility tree element"""
    id: str = Field(default_factory=lambda: f"el_{uuid.uuid4().hex[:8]}")
    role: str
    name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    disabled: bool = False
    focused: bool = False
    checked: Optional[bool] = None
    expanded: Optional[bool] = None
    required: bool = False
    invalid: Optional[bool] = None
    children: list["A11yElement"] = Field(default_factory=list)
    parent_id: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class AccessibilityTree(BaseModel):
    """Full accessibility tree snapshot"""
    id: str = Field(default_factory=lambda: f"a11y_{uuid.uuid4().hex[:12]}")
    url: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    title: Optional[str] = None
    root: A11yElement
    element_count: int = 0
    interactive_elements: list[str] = Field(default_factory=list)


class DOMElement(BaseModel):
    """DOM element for state extraction"""
    id: str
    tag: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    text_content: Optional[str] = None
    inner_html: Optional[str] = None
    children: list["DOMElement"] = Field(default_factory=list)
    xpath: Optional[str] = None
    css_selector: Optional[str] = None


class DOMSnapshot(BaseModel):
    """Full DOM state snapshot"""
    id: str = Field(default_factory=lambda: f"dom_{uuid.uuid4().hex[:12]}")
    url: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    root: DOMElement
    title: Optional[str] = None
    forms: list[dict[str, Any]] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)
    buttons: list[dict[str, Any]] = Field(default_factory=list)


class InteractionType(str, Enum):
    """User interaction types"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    TYPE = "type"
    HOVER = "hover"
    FOCUS = "focus"
    BLUR = "blur"
    SCROLL = "scroll"
    SUBMIT = "submit"
    SELECT = "select"
    DRAG = "drag"
    DROP = "drop"


class UserInteraction(BaseModel):
    """User interaction event"""
    id: str = Field(default_factory=lambda: f"int_{uuid.uuid4().hex[:12]}")
    interaction_type: InteractionType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    element_id: Optional[str] = None
    element_role: Optional[str] = None
    element_name: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    key: Optional[str] = None
    value: Optional[str] = None
    target_url: Optional[str] = None


class BehavioralSignal(BaseModel):
    """Extracted behavioral signal"""
    id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    signal_type: SignalType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerceptionProvider(ABC):
    """Abstract perception provider"""

    @abstractmethod
    async def get_accessibility_tree(self, url: str) -> AccessibilityTree:
        """Extract accessibility tree from URL"""
        pass

    @abstractmethod
    async def get_dom_snapshot(self, url: str) -> DOMSnapshot:
        """Extract DOM snapshot from URL"""
        pass

    @abstractmethod
    async def capture_screenshot(self, url: str, element_id: Optional[str] = None) -> bytes:
        """Capture screenshot"""
        pass

    @abstractmethod
    async def observe_interactions(self, url: str) -> list[UserInteraction]:
        """Observe user interactions"""
        pass


class SignalExtractor:
    """Extract signals from perception data"""

    def __init__(self):
        self._extractors = {
            SignalType.ACCESSIBILITY_TREE: self._extract_a11y_signals,
            SignalType.DOM_SNAPSHOT: self._extract_dom_signals,
            SignalType.USER_INTERACTION: self._extract_interaction_signals,
        }

    def extract(self, data: Any, signal_type: SignalType) -> list[BehavioralSignal]:
        """Extract signals from perception data"""
        extractor = self._extractors.get(signal_type)
        if extractor:
            return extractor(data)
        return []

    def _extract_a11y_signals(self, tree: AccessibilityTree) -> list[BehavioralSignal]:
        """Extract signals from accessibility tree"""
        signals = []
        
        # Detect forms
        forms = self._find_elements_by_role(tree.root, "form")
        if forms:
            signals.append(BehavioralSignal(
                signal_type=SignalType.ACCESSIBILITY_TREE,
                source=tree.url,
                payload={"type": "forms_detected", "count": len(forms)},
                metadata={"form_ids": [f.id for f in forms]}
            ))

        # Detect dialogs
        dialogs = self._find_elements_by_role(tree.root, "dialog")
        if dialogs:
            signals.append(BehavioralSignal(
                signal_type=SignalType.ACCESSIBILITY_TREE,
                source=tree.url,
                payload={"type": "dialogs_detected", "count": len(dialogs)},
                metadata={"dialog_ids": [d.id for d in dialogs]}
            ))

        # Detect alerts
        alerts = self._find_elements_by_role(tree.root, "alert")
        if alerts:
            signals.append(BehavioralSignal(
                signal_type=SignalType.ACCESSIBILITY_TREE,
                source=tree.url,
                payload={"type": "alerts_detected", "count": len(alerts)},
                confidence=0.9
            ))

        return signals

    def _extract_dom_signals(self, snapshot: DOMSnapshot) -> list[BehavioralSignal]:
        """Extract signals from DOM snapshot"""
        signals = []

        # Detect forms
        if snapshot.forms:
            signals.append(BehavioralSignal(
                signal_type=SignalType.DOM_SNAPSHOT,
                source=snapshot.url,
                payload={"type": "forms", "count": len(snapshot.forms)}
            ))

        # Detect inputs needing attention
        invalid_inputs = [i for i in snapshot.inputs if i.get("invalid")]
        if invalid_inputs:
            signals.append(BehavioralSignal(
                signal_type=SignalType.DOM_SNAPSHOT,
                source=snapshot.url,
                payload={"type": "invalid_inputs", "count": len(invalid_inputs)},
                confidence=0.8
            ))

        return signals

    def _extract_interaction_signals(self, interactions: list[UserInteraction]) -> list[BehavioralSignal]:
        """Extract signals from user interactions"""
        signals = []
        
        clicks = [i for i in interactions if i.interaction_type == InteractionType.CLICK]
        if len(clicks) > 10:
            signals.append(BehavioralSignal(
                signal_type=SignalType.USER_INTERACTION,
                source="interaction_stream",
                payload={"type": "high_click_activity", "count": len(clicks)},
                confidence=0.7
            ))

        form_submits = [i for i in interactions if i.interaction_type == InteractionType.SUBMIT]
        if form_submits:
            signals.append(BehavioralSignal(
                signal_type=SignalType.USER_INTERACTION,
                source="interaction_stream",
                payload={"type": "form_submissions", "count": len(form_submits)},
                confidence=0.95
            ))

        return signals

    def _find_elements_by_role(self, element: A11yElement, role: str) -> list[A11yElement]:
        """Find all elements with a specific role"""
        results = []
        if element.role.lower() == role.lower():
            results.append(element)
        for child in element.children:
            results.extend(self._find_elements_by_role(child, role))
        return results


class PerceptionService:
    """Main perception service"""

    def __init__(self, provider: Optional[PerceptionProvider] = None):
        self._provider = provider
        self._extractor = SignalExtractor()
        self._signal_history: list[BehavioralSignal] = []

    async def perceive(self, url: str, include: Optional[list[SignalType]] = None) -> dict[str, Any]:
        """Perceive URL and extract signals"""
        include = include or [SignalType.ACCESSIBILITY_TREE, SignalType.DOM_SNAPSHOT]
        results = {}

        if SignalType.ACCESSIBILITY_TREE in include and self._provider:
            tree = await self._provider.get_accessibility_tree(url)
            results["accessibility_tree"] = tree
            signals = self._extractor.extract(tree, SignalType.ACCESSIBILITY_TREE)
            results["signals"] = signals
            self._signal_history.extend(signals)

        if SignalType.DOM_SNAPSHOT in include and self._provider:
            snapshot = await self._provider.get_dom_snapshot(url)
            results["dom_snapshot"] = snapshot
            signals = self._extractor.extract(snapshot, SignalType.DOM_SNAPSHOT)
            results["signals"] = signals
            self._signal_history.extend(signals)

        return results

    def get_signals(self, limit: int = 100) -> list[BehavioralSignal]:
        """Get recent signals"""
        return self._signal_history[-limit:]

    def clear_signals(self):
        """Clear signal history"""
        self._signal_history.clear()

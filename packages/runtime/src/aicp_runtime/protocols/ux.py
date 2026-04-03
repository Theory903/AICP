"""UX Cognitive Protocol for AICP.

Governs agent-human interaction surfaces.  Every interaction the agent
initiates with a human goes through this protocol so that:
  - Interactions are structured and auditable.
  - The agent tracks conversation turns per session.
  - Choice blocks respect a configurable max-options limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class UXProtocolError(Exception):
    """Raised when a UX protocol constraint is violated."""


# ---------------------------------------------------------------------------
# InteractionType enum
# ---------------------------------------------------------------------------


class InteractionType(str, Enum):
    QUESTION = "question"
    CHOICE = "choice"
    CONFIRMATION = "confirmation"
    NOTIFICATION = "notification"


# ---------------------------------------------------------------------------
# PromptBlock
# ---------------------------------------------------------------------------


@dataclass
class PromptBlock:
    """A structured interaction block the agent surfaces to the user."""

    interaction_type: InteractionType
    message: str
    options: Optional[list[str]] = None
    default: Optional[str] = None

    def render(self) -> str:
        """Return a human-readable representation of this block."""
        lines: list[str] = [f"[{self.interaction_type.value.upper()}] {self.message}"]
        if self.options:
            for idx, opt in enumerate(self.options, 1):
                lines.append(f"  {idx}. {opt}")
        if self.default is not None:
            lines.append(f"  (default: {self.default})")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_type": self.interaction_type.value,
            "message": self.message,
            "options": self.options,
            "default": self.default,
        }


# ---------------------------------------------------------------------------
# UXProtocol
# ---------------------------------------------------------------------------

_DEFAULT_MAX_OPTIONS = 10


class UXProtocol:
    """Manages structured agent-human interactions for a session."""

    def __init__(self, max_options: int = _DEFAULT_MAX_OPTIONS) -> None:
        self._max_options = max_options
        self._history: list[PromptBlock] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def turn_count(self) -> int:
        return len(self._history)

    @property
    def history(self) -> list[PromptBlock]:
        return list(self._history)

    # ------------------------------------------------------------------
    # Interaction builders
    # ------------------------------------------------------------------

    def ask(self, message: str) -> PromptBlock:
        """Create a free-text QUESTION block."""
        block = PromptBlock(interaction_type=InteractionType.QUESTION, message=message)
        self._record(block)
        return block

    def choose(self, message: str, options: list[str]) -> PromptBlock:
        """Create a CHOICE block with a finite set of options."""
        if not options:
            raise UXProtocolError("options must not be empty")
        if len(options) > self._max_options:
            raise UXProtocolError(
                f"max_options exceeded: {len(options)} > {self._max_options}"
            )
        block = PromptBlock(
            interaction_type=InteractionType.CHOICE,
            message=message,
            options=list(options),
        )
        self._record(block)
        return block

    def confirm(self, message: str, default: str = "yes") -> PromptBlock:
        """Create a CONFIRMATION block (yes/no with optional default)."""
        block = PromptBlock(
            interaction_type=InteractionType.CONFIRMATION,
            message=message,
            default=default,
        )
        self._record(block)
        return block

    def notify(self, message: str) -> PromptBlock:
        """Create a one-way NOTIFICATION block."""
        block = PromptBlock(
            interaction_type=InteractionType.NOTIFICATION, message=message
        )
        self._record(block)
        return block

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, block: PromptBlock) -> None:
        self._history.append(block)

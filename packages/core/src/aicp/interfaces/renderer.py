"""Renderer interface.

Defines the contract for rendering execution results for display.
Renderers provide hints on how to display results to users.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class RenderFormat(str, Enum):
    """Format hint for rendering."""

    TEXT = "text"
    JSON = "json"
    TABLE = "table"
    CODE = "code"
    IMAGE = "image"
    ERROR = "error"
    PROGRESS = "progress"
    CONFIRMATION = "confirmation"


class RenderHints(BaseModel):
    """Hints for how to render a result."""

    format: RenderFormat = RenderFormat.TEXT
    title: str | None = None
    description: str | None = None
    fields: list[str] | None = None  # Fields to display
    max_length: int | None = None
    truncate: bool = True
    syntax: str | None = None  # For code: "python", "json", etc.
    table_columns: list[str] | None = None
    next_actions: list[dict[str, Any]] = []  # Suggested next actions


class Renderer(ABC):
    """Abstract interface for rendering execution results.

    Renderers interpret execution results and provide display hints.
    Different renderers can handle different output formats or contexts
    (CLI, web UI, etc.).
    """

    @property
    @abstractmethod
    def renderer_type(self) -> str:
        """Type identifier for this renderer."""
        pass

    @abstractmethod
    def render(self, result: Any, hints: RenderHints | None = None) -> str:
        """Render a result for display.

        Args:
            result: The result to render.
            hints: Optional rendering hints.

        Returns:
            Rendered string representation.
        """
        pass

    @abstractmethod
    def render_error(self, error: Exception) -> str:
        """Render an error for display.

        Args:
            error: The error to render.

        Returns:
            Rendered error string.
        """
        pass

    @abstractmethod
    def render_table(
        self,
        data: list[dict[str, Any]],
        columns: list[str] | None = None,
    ) -> str:
        """Render data as a table.

        Args:
            data: List of records to render.
            columns: Optional list of columns to include.

        Returns:
            Rendered table string.
        """
        pass

    def generate_hints(self, result: Any, context: dict[str, Any] | None = None) -> RenderHints:
        """Generate rendering hints for a result.

        Default implementation analyzes result type.
        Renderers can override with more sophisticated logic.

        Args:
            result: The result to generate hints for.
            context: Optional context for hint generation.

        Returns:
            Generated RenderHints.
        """
        hints = RenderHints()

        if isinstance(result, dict):
            hints.format = RenderFormat.JSON
        elif isinstance(result, list):
            if result and all(isinstance(r, dict) for r in result):
                hints.format = RenderFormat.TABLE
            else:
                hints.format = RenderFormat.TEXT
        elif isinstance(result, str):
            hints.format = RenderFormat.TEXT
        else:
            hints.format = RenderFormat.TEXT

        return hints

"""Renderer interface.

Defines the contract for rendering execution results for display.
Renderers provide hints on how to display results to users.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(extra="forbid")

    format: RenderFormat = RenderFormat.TEXT
    title: str | None = None
    description: str | None = None
    fields: list[str] | None = None
    max_length: int | None = Field(default=None, ge=1)
    truncate: bool = True
    syntax: str | None = None
    table_columns: list[str] | None = None
    next_actions: list[dict[str, Any]] = Field(default_factory=list)


class Renderer(ABC):
    """Abstract interface for rendering execution results.

    Renderers interpret execution results and provide display hints.
    Different renderers can handle different output formats or contexts
    such as CLI or web UI.
    """

    @property
    @abstractmethod
    def renderer_type(self) -> str:
        """Type identifier for this renderer."""
        raise NotImplementedError

    @abstractmethod
    def render(self, result: Any, hints: RenderHints | None = None) -> str:
        """Render a result for display.

        Args:
            result: The result to render.
            hints: Optional rendering hints.

        Returns:
            Rendered string representation.
        """
        raise NotImplementedError

    @abstractmethod
    def render_error(self, error: Exception) -> str:
        """Render an error for display.

        Args:
            error: The error to render.

        Returns:
            Rendered error string.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def generate_hints(
        self,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> RenderHints:
        """Generate rendering hints for a result.

        Default implementation analyzes result shape.
        Renderers can override with more sophisticated logic.
        """
        context = context or {}
        hints = RenderHints()

        forced_format = context.get("format")
        if forced_format:
            try:
                hints.format = (
                    forced_format
                    if isinstance(forced_format, RenderFormat)
                    else RenderFormat(forced_format)
                )
                return hints
            except ValueError:
                pass

        if isinstance(result, Exception):
            hints.format = RenderFormat.ERROR
            hints.title = type(result).__name__
            hints.description = str(result)
            return hints

        if isinstance(result, dict):
            if result and all(not isinstance(value, (dict, list)) for value in result.values()):
                hints.format = RenderFormat.TABLE
                hints.table_columns = list(result.keys())
            else:
                hints.format = RenderFormat.JSON
            return hints

        if isinstance(result, list):
            if result and all(isinstance(item, dict) for item in result):
                hints.format = RenderFormat.TABLE
                first_row = result[0]
                hints.table_columns = list(first_row.keys())
            else:
                hints.format = RenderFormat.JSON if result else RenderFormat.TEXT
            return hints

        if isinstance(result, str):
            stripped = result.lstrip()
            if stripped.startswith("{") or stripped.startswith("["):
                hints.format = RenderFormat.JSON
            else:
                hints.format = RenderFormat.TEXT
                if len(result) > 1000:
                    hints.max_length = 1000
                    hints.truncate = True
            return hints

        if isinstance(result, (int, float, bool)) or result is None:
            hints.format = RenderFormat.TEXT
            return hints

        hints.format = RenderFormat.TEXT
        return hints
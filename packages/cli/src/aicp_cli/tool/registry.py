"""Tool registry for discoverable tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ToolInfo:
    """Information about a registered tool."""

    name: str
    category: str
    tool_class: type["AicpTool"]
    spec: "ToolSpec"
    file_path: str | None = None


class ToolRegistry:
    """Registry for all AICP tools with discovery capabilities."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._categories = {}
        return cls._instance

    def __init__(self):
        pass

    def register(self, tool_class: type["AicpTool"], spec: "ToolSpec", file_path: str | None = None) -> None:
        """Register a tool."""
        self._tools[spec.name] = ToolInfo(
            name=spec.name,
            category=spec.category,
            tool_class=tool_class,
            spec=spec,
            file_path=file_path,
        )

        category = spec.category.split(".")[0] if "." in spec.category else spec.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(spec.name)

    def get(self, name: str) -> ToolInfo | None:
        """Get tool by name."""
        return self._tools.get(name)

    def get_by_category(self, category: str) -> list[ToolInfo]:
        """Get all tools in a category."""
        return [
            info for info in self._tools.values()
            if info.category.split(".")[0] == category
        ]

    def list_all(self) -> list[ToolInfo]:
        """List all registered tools."""
        return list(self._tools.values())

    def search(self, query: str) -> list[ToolInfo]:
        """Search tools by name, description, or tags."""
        query = query.lower()
        results = []
        for info in self._tools.values():
            if query in info.name.lower():
                results.append(info)
            elif query in info.spec.description.lower():
                results.append(info)
            elif any(query in tag.lower() for tag in info.spec.tags):
                results.append(info)
        return results

    def get_tool_instance(self, name: str, **kwargs) -> "AicpTool | None":
        """Get an instance of a tool."""
        info = self._tools.get(name)
        if info:
            return info.tool_class(info.spec, **kwargs)
        return None

    def export_discovery(self) -> dict[str, Any]:
        """Export all tools in discovery format."""
        tools = []
        for info in self._tools.values():
            tools.append({
                "name": info.spec.name,
                "description": info.spec.description,
                "kind": info.spec.kind.value,
                "category": info.spec.category,
                "tags": info.spec.tags,
                "side_effect": info.spec.side_effect.value,
                "risk_level": info.spec.risk_level.value,
                "input_schema": info.spec.input_schema,
                "output_schema": info.spec.output_schema,
                "next_capabilities": info.spec.next_capabilities,
            })
        return {"tools": tools, "count": len(tools)}

    def save_to_file(self, path: str | Path) -> None:
        """Save registry to JSON file."""
        with open(path, "w") as f:
            json.dump(self.export_discovery(), f, indent=2)

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (useful for testing)."""
        if cls._instance:
            cls._instance._tools = {}
            cls._instance._categories = {}


def register_tool(spec: "ToolSpec", category: str | None = None):
    """Decorator to register a tool class."""
    def decorator(tool_class: type["AicpTool"]) -> type["AicpTool"]:
        registry = ToolRegistry()
        cat = category or spec.category
        registry.register(tool_class, spec)
        return tool_class
    return decorator
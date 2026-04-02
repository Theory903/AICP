"""Base tool class with permission and explain methods."""

from __future__ import annotations

import fnmatch
import json
import re
from abc import ABC, abstractmethod
from typing import Any


class AicpTool(ABC):
    """Base class for all AICP tools with permission and explain capabilities."""

    def __init__(self, spec: "ToolSpec"):
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def category(self) -> str:
        return self.spec.category

    def get_permission_pattern(self) -> str:
        """Get permission pattern for this tool."""
        return self.spec.get_permission_pattern()

    def get_permission_description(self) -> str:
        """Get human-readable permission description."""
        if self.spec.permission_description:
            return self.spec.permission_description
        return f"{self.spec.name}: {self.spec.description}"

    def check_permission(
        self,
        user_permissions: list[str],
        mode: str = "default",
    ) -> tuple[bool, str | None]:
        """
        Check if tool is permitted based on user permissions.
        
        Args:
            user_permissions: List of permission patterns (supports wildcards)
            mode: Permission mode - 'default', 'plan', 'bypassPermissions', 'auto'
        
        Returns:
            Tuple of (is_permitted, reason_if_not)
        """
        if mode == "bypassPermissions":
            return True, None

        if mode == "plan":
            return True, "Plan mode bypasses permission checks"

        if mode == "auto":
            if self.spec.risk_level.value in ("none", "low"):
                return True, None

        pattern = self.get_permission_pattern()

        for perm in user_permissions:
            if self._match_permission(perm, pattern):
                return True, None

        return False, f"Missing permission: {pattern}"

    def _match_permission(self, permission: str, tool_pattern: str) -> bool:
        """Match permission pattern against tool pattern with wildcard support."""
        perm_parts = permission.split("(")
        tool_parts = tool_pattern.split("(")

        if len(perm_parts) != 2 or len(tool_parts) != 2:
            return permission == tool_pattern

        perm_prefix = perm_parts[0].strip()
        perm_tools = perm_parts[1].rstrip(")").split(",") if len(perm_parts) > 1 else []

        tool_prefix = tool_parts[0].strip()
        tool_name = tool_parts[1].rstrip(")") if len(tool_parts) > 1 else ""

        if not fnmatch.fnmatch(tool_prefix, perm_prefix):
            return False

        for perm_tool in perm_tools:
            perm_tool = perm_tool.strip()
            if fnmatch.fnmatch(tool_name, perm_tool):
                return True

        return False

    def explain(self, format: str = "text") -> str | dict[str, Any]:
        """
        Explain what this tool does in human-readable format.
        
        Args:
            format: Output format - 'text', 'json', or 'markdown'
        
        Returns:
            Explanation in requested format
        """
        explanation = {
            "name": self.spec.name,
            "description": self.spec.description,
            "category": self.spec.category,
            "kind": self.spec.kind.value,
            "side_effect": self.spec.side_effect.value,
            "risk": self.spec.risk_level.value,
            "requires_approval": self.spec.requires_approval,
            "idempotent": self.spec.idempotency_key is not None,
            "permission": self.get_permission_pattern(),
            "input": self._explain_schema(self.spec.input_schema),
            "output": self._explain_schema(self.spec.output_schema),
            "next_actions": self.spec.next_capabilities,
            "tags": self.spec.tags,
        }

        if format == "json":
            return explanation

        if format == "markdown":
            return self._explain_markdown(explanation)

        return self._explain_text(explanation)

    def _explain_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Explain schema in human-readable terms."""
        if not schema:
            return {"type": "object", "properties": {}}

        props = schema.get("properties", {})
        explained = {}
        required = schema.get("required", [])

        for name, prop in props.items():
            explained[name] = {
                "type": prop.get("type", "any"),
                "description": prop.get("description", ""),
                "required": name in required,
            }
            if "enum" in prop:
                explained[name]["options"] = prop["enum"]

        return {"type": schema.get("type", "object"), "properties": explained}

    def _explain_text(self, exp: dict[str, Any]) -> str:
        """Format explanation as plain text."""
        lines = [
            f"Tool: {exp['name']}",
            f"Category: {exp['category']}",
            f"Description: {exp['description']}",
            f"",
            f"Kind: {exp['kind']}",
            f"Side Effect: {exp['side_effect']}",
            f"Risk: {exp['risk']}",
            f"Requires Approval: {exp['requires_approval']}",
            f"Permission: {exp['permission']}",
        ]

        if exp["input"]["properties"]:
            lines.append("")
            lines.append("Input:")
            for name, prop in exp["input"]["properties"].items():
                required = " (required)" if prop.get("required") else ""
                lines.append(f"  - {name}: {prop['type']}{required}")
                if prop.get("description"):
                    lines.append(f"    {prop['description']}")

        if exp["next_actions"]:
            lines.append("")
            lines.append(f"Next Actions: {', '.join(exp['next_actions'])}")

        return "\n".join(lines)

    def _explain_markdown(self, exp: dict[str, Any]) -> str:
        """Format explanation as markdown."""
        lines = [
            f"# {exp['name']}",
            "",
            f"**Category:** {exp['category']}",
            f"**Kind:** {exp['kind']}",
            f"**Risk:** {exp['risk']}",
            "",
            exp["description"],
            "",
            "## Details",
            "",
            f"- **Side Effect:** {exp['side_effect']}",
            f"- **Requires Approval:** {exp['requires_approval']}",
            f"- **Permission:** `{exp['permission']}`",
        ]

        if exp["input"]["properties"]:
            lines.append("")
            lines.append("## Input Parameters")
            lines.append("")
            for name, prop in exp["input"]["properties"].items():
                required = " *(required)*" if prop.get("required") else ""
                lines.append(f"- `{name}`: {prop['type']}{required}")
                if prop.get("description"):
                    lines.append(f"  - {prop['description']}")

        if exp["output"]["properties"]:
            lines.append("")
            lines.append("## Output")
            lines.append("")
            for name, prop in exp["output"]["properties"].items():
                lines.append(f"- `{name}`: {prop['type']}")

        if exp["next_actions"]:
            lines.append("")
            lines.append("## Next Actions")
            lines.append("")
            for action in exp["next_actions"]:
                lines.append(f"- `{action}`")

        return "\n".join(lines)

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> Any:
        """Execute the tool with given arguments."""
        pass

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate arguments against input schema."""
        schema = self.spec.input_schema
        required = schema.get("required", [])

        for req in required:
            if req not in args:
                return False, f"Missing required argument: {req}"

        return True, None

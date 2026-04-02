"""Capability family tools - tool implementations for capability.* family."""

from typing import Any

from aicp_cli.tool import AicpTool, ToolSpec, ToolKind, SideEffectClass, RiskLevel


class ListCapabilitiesTool(AicpTool):
    """List all available capabilities."""

    def __init__(self, spec: ToolSpec):
        super().__init__(spec)
        self._capabilities = []

    def set_capabilities(self, capabilities: list[dict]) -> None:
        """Set capabilities to list."""
        self._capabilities = capabilities

    def execute(self, args: dict[str, Any]) -> Any:
        """List capabilities."""
        filter_kind = args.get("kind")
        filter_tag = args.get("tag")

        results = self._capabilities
        if filter_kind:
            results = [c for c in results if c.get("kind") == filter_kind]
        if filter_tag:
            results = [c for c in results if filter_tag in c.get("tags", [])]

        return {
            "capabilities": results,
            "count": len(results),
        }


class DescribeCapabilityTool(AicpTool):
    """Describe a specific capability in detail."""

    def __init__(self, spec: ToolSpec):
        super().__init__(spec)
        self._capabilities = {}

    def set_capabilities(self, capabilities: dict) -> None:
        """Set capabilities map."""
        self._capabilities = capabilities

    def execute(self, args: dict[str, Any]) -> Any:
        """Describe a capability."""
        name = args.get("name")
        format_type = args.get("format", "text")

        cap = self._capabilities.get(name)
        if not cap:
            return {"error": f"Capability not found: {name}"}

        if format_type == "json":
            return cap

        return {
            "name": cap.get("name"),
            "description": cap.get("description"),
            "kind": cap.get("kind"),
            "input_schema": cap.get("input_schema"),
            "output_schema": cap.get("output_schema"),
            "tags": cap.get("tags", []),
        }


class CallCapabilityTool(AicpTool):
    """Call/execute a capability."""

    def execute(self, args: dict[str, Any]) -> Any:
        """Execute a capability call."""
        name = args.get("name")
        params = args.get("params", {})

        return {
            "capability": name,
            "params": params,
            "status": "executed",
            "session_id": args.get("session_id"),
        }
"""Workflow family tools - tool implementations for workflow.* family."""

from typing import Any

from aicp_cli.tool import AicpTool, ToolSpec, ToolKind, SideEffectClass, RiskLevel


class ListWorkflowsTool(AicpTool):
    """List all available workflows."""

    def __init__(self, spec: ToolSpec):
        super().__init__(spec)
        self._workflows = []

    def set_workflows(self, workflows: list[dict]) -> None:
        """Set workflows to list."""
        self._workflows = workflows

    def execute(self, args: dict[str, Any]) -> Any:
        """List workflows."""
        filter_status = args.get("status")
        filter_tag = args.get("tag")

        results = self._workflows
        if filter_status:
            results = [w for w in results if w.get("status") == filter_status]
        if filter_tag:
            results = [w for w in results if filter_tag in w.get("tags", [])]

        return {
            "workflows": results,
            "count": len(results),
        }


class RunWorkflowTool(AicpTool):
    """Execute a workflow."""

    def execute(self, args: dict[str, Any]) -> Any:
        """Run a workflow."""
        name = args.get("name")
        params = args.get("params", {})
        resume = args.get("resume")
        workflow_id = args.get("workflow_id")

        return {
            "workflow": name,
            "params": params,
            "status": "started",
            "workflow_id": workflow_id or f"wf_{name}_{id(args)}",
            "resumed": resume,
        }


class DescribeWorkflowTool(AicpTool):
    """Describe a workflow's steps."""

    def __init__(self, spec: ToolSpec):
        super().__init__(spec)
        self._workflows = {}

    def set_workflows(self, workflows: dict) -> None:
        """Set workflows map."""
        self._workflows = workflows

    def execute(self, args: dict[str, Any]) -> Any:
        """Describe a workflow."""
        name = args.get("name")

        wf = self._workflows.get(name)
        if not wf:
            return {"error": f"Workflow not found: {name}"}

        return {
            "name": wf.get("name"),
            "description": wf.get("description"),
            "steps": wf.get("steps", []),
            "graph": wf.get("graph"),
        }

"""AICP Registry.

Central registry for capabilities, policies, and workflows.
"""

from typing import Any

from aicp.capability import Capability
from aicp.interfaces.policy_engine import Policy


class AicpRegistry:
    """Central registry for AICP resources.

    Manages capabilities, policies, and workflow templates.
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._policies: dict[str, Policy] = {}
        self._workflows: dict[str, dict[str, Any]] = {}

    def register_capability(self, capability: Capability) -> None:
        """Register a capability."""
        self._capabilities[capability.name] = capability

    def get_capability(self, name: str) -> Capability | None:
        """Get a capability by name."""
        return self._capabilities.get(name)

    def list_capabilities(self) -> list[Capability]:
        """List all registered capabilities."""
        return list(self._capabilities.values())

    def unregister_capability(self, name: str) -> bool:
        """Unregister a capability."""
        if name in self._capabilities:
            del self._capabilities[name]
            return True
        return False

    def register_policy(self, policy: Policy) -> None:
        """Register a policy."""
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Policy | None:
        """Get a policy by name."""
        return self._policies.get(name)

    def list_policies(self) -> list[Policy]:
        """List all registered policies."""
        return list(self._policies.values())

    def unregister_policy(self, name: str) -> bool:
        """Unregister a policy."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def register_workflow_template(self, name: str, template: dict[str, Any]) -> None:
        """Register a workflow template."""
        self._workflows[name] = template

    def get_workflow_template(self, name: str) -> dict[str, Any] | None:
        """Get a workflow template by name."""
        return self._workflows.get(name)

    def list_workflow_templates(self) -> list[dict[str, Any]]:
        """List all workflow templates."""
        return list(self._workflows.values())

    def discovery_response(self) -> dict[str, Any]:
        """Generate discovery response."""
        return {
            "version": "0.1.0",
            "capabilities": [
                cap.model_dump(exclude_none=True) for cap in self._capabilities.values()
            ],
            "policies": [pol.model_dump(exclude_none=True) for pol in self._policies.values()],
            "workflows": list(self._workflows.values()),
            "metadata": {
                "capability_count": len(self._capabilities),
                "policy_count": len(self._policies),
                "workflow_count": len(self._workflows),
            },
        }

    def clear(self) -> None:
        """Clear all registered resources."""
        self._capabilities.clear()
        self._policies.clear()
        self._workflows.clear()

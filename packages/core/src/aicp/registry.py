"""AICP Registry.

Central registry for capabilities, policies, and workflows.
"""

from __future__ import annotations

from typing import Any

from aicp.capability import Capability
from aicp.interfaces.policy_engine import Policy


class TagSearchStrategy:
    """Tag-based search strategy for capabilities.

    Ranks capabilities by tag match score and keyword relevance.
    """

    def __init__(self, registry: AicpRegistry):
        self._registry = registry

    def search(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[Capability]:
        """Search capabilities by query and optional tags.

        Args:
            query: Natural language search query.
            tags: Optional list of required tags (any match).
            limit: Maximum results to return.

        Returns:
            Ranked list of matching capabilities.
        """
        cleaned_query = query.strip().lower()
        normalized_tags = {tag.lower() for tag in (tags or []) if tag.strip()}
        query_terms = [term for term in cleaned_query.split() if term]

        capabilities = self._registry.list_capabilities()
        scored: list[tuple[int, str, Capability]] = []

        for capability in capabilities:
            name = capability.name.lower()
            description = (capability.description or "").lower()
            capability_tags = {tag.lower() for tag in (capability.tags or [])}

            score = 0

            if normalized_tags:
                if capability_tags.intersection(normalized_tags):
                    score += 50
                else:
                    continue

            if cleaned_query:
                if name == cleaned_query:
                    score += 140
                elif name.startswith(cleaned_query):
                    score += 100
                elif cleaned_query in name:
                    score += 60

                if cleaned_query in description:
                    score += 30

            for term in query_terms:
                if term == name:
                    score += 40
                elif term in name:
                    score += 20

                if term in description:
                    score += 10

                if any(term in tag for tag in capability_tags):
                    score += 15

            if score > 0 or (not cleaned_query and normalized_tags):
                scored.append((score, capability.name, capability))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [capability for _, _, capability in scored[: max(0, limit)]]


class AicpRegistry:
    """Central registry for AICP resources.

    Manages capabilities, policies, and workflow templates.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._policies: dict[str, Policy] = {}
        self._workflows: dict[str, dict[str, Any]] = {}
        self._search_strategy = TagSearchStrategy(self)

    def register_capability(self, capability: Capability, *, overwrite: bool = True) -> None:
        """Register a capability."""
        if not overwrite and capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def get_capability(self, name: str) -> Capability | None:
        """Get a capability by name."""
        return self._capabilities.get(name)

    def require_capability(self, name: str) -> Capability:
        """Get a capability by name or raise."""
        capability = self.get_capability(name)
        if capability is None:
            raise KeyError(f"Capability not found: {name}")
        return capability

    def list_capabilities(self) -> list[Capability]:
        """List all registered capabilities."""
        return [self._capabilities[name] for name in sorted(self._capabilities)]

    def search_capabilities(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[Capability]:
        """Search capabilities by query and optional tags.

        Uses TagSearchStrategy for ranking results.

        Args:
            query: Natural language search query.
            tags: Optional list of required tags.
            limit: Maximum results to return.

        Returns:
            Ranked list of matching capabilities.
        """
        return self._search_strategy.search(query, tags, limit)

    def unregister_capability(self, name: str) -> bool:
        """Unregister a capability."""
        return self._capabilities.pop(name, None) is not None

    def register_policy(self, policy: Policy, *, overwrite: bool = True) -> None:
        """Register a policy."""
        if not overwrite and policy.name in self._policies:
            raise ValueError(f"Policy already registered: {policy.name}")
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Policy | None:
        """Get a policy by name."""
        return self._policies.get(name)

    def require_policy(self, name: str) -> Policy:
        """Get a policy by name or raise."""
        policy = self.get_policy(name)
        if policy is None:
            raise KeyError(f"Policy not found: {name}")
        return policy

    def list_policies(self) -> list[Policy]:
        """List all registered policies."""
        return [self._policies[name] for name in sorted(self._policies)]

    def unregister_policy(self, name: str) -> bool:
        """Unregister a policy."""
        return self._policies.pop(name, None) is not None

    def register_workflow_template(
        self,
        name: str,
        template: dict[str, Any],
        *,
        overwrite: bool = True,
    ) -> None:
        """Register a workflow template."""
        if not overwrite and name in self._workflows:
            raise ValueError(f"Workflow template already registered: {name}")
        self._workflows[name] = template

    def get_workflow_template(self, name: str) -> dict[str, Any] | None:
        """Get a workflow template by name."""
        return self._workflows.get(name)

    def require_workflow_template(self, name: str) -> dict[str, Any]:
        """Get a workflow template by name or raise."""
        template = self.get_workflow_template(name)
        if template is None:
            raise KeyError(f"Workflow template not found: {name}")
        return template

    def list_workflow_templates(self) -> list[dict[str, Any]]:
        """List all workflow templates."""
        return [self._workflows[name] for name in sorted(self._workflows)]

    def discovery_response(self) -> dict[str, Any]:
        """Generate discovery response."""
        capabilities = self.list_capabilities()
        policies = self.list_policies()
        workflows = self.list_workflow_templates()

        return {
            "version": "0.1.1",
            "capabilities": [
                capability.model_dump(exclude_none=True) for capability in capabilities
            ],
            "policies": [
                policy.model_dump(exclude_none=True) for policy in policies
            ],
            "workflows": workflows,
            "metadata": {
                "capability_count": len(capabilities),
                "policy_count": len(policies),
                "workflow_count": len(workflows),
            },
        }

    def clear(self) -> None:
        """Clear all registered resources."""
        self._capabilities.clear()
        self._policies.clear()
        self._workflows.clear()

    def counts(self) -> dict[str, int]:
        """Return registry object counts."""
        return {
            "capabilities": len(self._capabilities),
            "policies": len(self._policies),
            "workflows": len(self._workflows),
        }

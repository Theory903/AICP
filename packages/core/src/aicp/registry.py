"""AICP Registry.

Central registry for capabilities, policies, and workflows.
"""

from typing import Any

from aicp.capability import Capability
from aicp.interfaces.policy_engine import Policy


class TagSearchStrategy:
    """Tag-based search strategy for capabilities.
    
    Ranks capabilities by tag match score and keyword relevance.
    """
    
    def __init__(self, registry: "AicpRegistry"):
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
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        capabilities = self._registry.list_capabilities()
        scored = []
        
        for cap in capabilities:
            score = 0
            
            if tags:
                if any(tag in cap.tags for tag in tags):
                    score += 50
                else:
                    continue
                    
            if cap.name.lower().startswith(query_lower):
                score += 100
            elif query_lower in cap.name.lower():
                score += 50
                
            if query_lower in cap.description.lower():
                score += 30
                
            for term in query_terms:
                if term in cap.name.lower():
                    score += 20
                if term in cap.description.lower():
                    score += 10
                if any(term in tag.lower() for tag in cap.tags):
                    score += 15
                    
            if score > 0:
                scored.append((score, cap))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        return [cap for _, cap in scored[:limit]]


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
        strategy = TagSearchStrategy(self)
        return strategy.search(query, tags, limit)

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

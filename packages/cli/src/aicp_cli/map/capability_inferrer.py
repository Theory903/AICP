"""Capability inferrer - infers capability candidates from extracted data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aicp_cli.map.route_extractor import ExtractedRoute
from aicp_cli.map.entity_mapper import ExtractedEntity
from aicp_cli.map.service_mapper import ExtractedService


@dataclass
class CapabilityCandidate:
    """A inferred capability candidate."""

    name: str
    description: str
    kind: str
    family: str

    source_route: str | None = None
    source_service: str | None = None

    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    side_effect_level: str = "unknown"
    risk_level: str = "low"
    approval_required: bool = False


class CapabilityInferrer:
    """Infers capability candidates from extracted data."""

    FAMILIES = {
        "users": ["user", "account", "profile", "auth", "login", "register"],
        "orders": ["order", "cart", "checkout", "purchase"],
        "payments": ["payment", "transaction", "refund", "charge", "invoice"],
        "products": ["product", "item", "inventory", "catalog"],
        "notifications": ["notification", "email", "message", "alert"],
        "admin": ["admin", "config", "settings", "system"],
    }

    HIGH_RISK_PATTERNS = ["payment", "refund", "delete", "admin", "transfer", "auth"]

    def infer(
        self,
        routes: list[ExtractedRoute],
        entities: list[ExtractedEntity],
        services: list[ExtractedService],
    ) -> list[CapabilityCandidate]:
        """Infer capability candidates from extracted data."""
        capabilities = []

        # Infer from routes
        for route in routes:
            caps = self._infer_from_route(route)
            capabilities.extend(caps)

        # Infer from services
        for service in services:
            caps = self._infer_from_service(service)
            capabilities.extend(caps)

        # De-duplicate by name
        seen = set()
        unique = []
        for cap in capabilities:
            if cap.name not in seen:
                seen.add(cap.name)
                unique.append(cap)

        return unique

    def _infer_from_route(self, route: ExtractedRoute) -> list[CapabilityCandidate]:
        """Infer capabilities from a route."""
        caps = []

        # Determine family from path
        family = self._get_family_from_path(route.path)

        # Determine action from method + path
        action = self._get_action_from_method(route.method, route.path)

        # Build capability name
        name = f"{family}.{action}" if family else action

        cap = CapabilityCandidate(
            name=name,
            description=f"{route.method.upper()} {route.path}",
            kind="action" if route.method in ["POST", "PUT", "PATCH", "DELETE"] else "query",
            family=family or "unknown",
            source_route=route.path,
            side_effect_level=self._estimate_side_effect(route),
            risk_level=self._estimate_risk(route),
            approval_required=self._requires_approval(route),
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )

        caps.append(cap)
        return caps

    def _infer_from_service(self, service: ExtractedService) -> list[CapabilityCandidate]:
        """Infer capabilities from a service."""
        caps = []

        family = self._get_family_from_name(service.name)

        for method in service.methods:
            action = method.lower()
            name = f"{family}.{action}" if family else action

            cap = CapabilityCandidate(
                name=name,
                description=f"Service method: {service.name}.{method}()",
                kind="action",
                family=family or "service",
                source_service=service.name,
                side_effect_level="write",
                risk_level="medium",
            )
            caps.append(cap)

        return caps

    def _get_family_from_path(self, path: str) -> str:
        """Get family from API path."""
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        if segments:
            return segments[0].lower()
        return "api"

    def _get_family_from_name(self, name: str) -> str:
        """Get family from service/entity name."""
        name_lower = name.lower()
        for family, keywords in self.FAMILIES.items():
            if any(kw in name_lower for kw in keywords):
                return family
        return "service"

    def _get_action_from_method(self, method: str, path: str) -> str:
        """Get action from HTTP method and path."""
        # Map HTTP method to action
        method_actions = {
            "get": "get",
            "post": "create",
            "put": "update",
            "patch": "update",
            "delete": "delete",
        }

        action = method_actions.get(method.lower(), "execute")

        # Add resource from path
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        if len(segments) > 1:
            resource = segments[-1].rstrip("s")
            if action in ["get", "create"]:
                return f"{action}_{resource}"
            elif action in ["update", "delete"]:
                # For /users/{id}, action is just the verb
                return action

        return action

    def _estimate_side_effect(self, route: ExtractedRoute) -> str:
        """Estimate side effect level from route."""
        if route.method.upper() in ["GET", "OPTIONS", "HEAD"]:
            return "read"
        elif route.method.upper() in ["POST", "PUT", "PATCH"]:
            return "write"
        elif route.method.upper() == "DELETE":
            return "write"
        return "unknown"

    def _estimate_risk(self, route: ExtractedRoute) -> str:
        """Estimate risk level from route."""
        path_lower = route.path.lower()
        for pattern in self.HIGH_RISK_PATTERNS:
            if pattern in path_lower:
                return "high"
        if route.method == "DELETE":
            return "medium"
        return "low"

    def _requires_approval(self, route: ExtractedRoute) -> bool:
        """Determine if route requires approval."""
        risk = self._estimate_risk(route)
        return risk in ["high", "medium"]
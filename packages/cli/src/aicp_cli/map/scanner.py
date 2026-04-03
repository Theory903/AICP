"""Main map scanner - orchestrates all extraction and inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aicp_cli.map.framework_detector import FrameworkDetector
from aicp_cli.map.route_extractor import RouteExtractor, ExtractedRoute
from aicp_cli.map.entity_mapper import EntityMapper, ExtractedEntity
from aicp_cli.map.service_mapper import ServiceMapper, ExtractedService
from aicp_cli.map.capability_inferrer import CapabilityInferrer, CapabilityCandidate
from aicp_cli.map.frontend_extractor import FrontendExtractor
from aicp_cli.map.linker import CrossLayerLinker


@dataclass
class MapResult:
    """Result of a map scan operation."""

    backend_framework: str | None
    backend_confidence: float = 0.0

    frontend_framework: str | None = None

    routes: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)

    pages: list[dict] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    frontend_api_calls: list[dict] = field(default_factory=list)

    capability_candidates: list[dict] = field(default_factory=list)
    workflow_candidates: list[dict] = field(default_factory=list)

    cross_links: int = 0
    link_confidence_high: int = 0
    link_confidence_medium: int = 0

    risk_summary: dict[str, int] = field(default_factory=dict)
    family_summary: dict[str, int] = field(default_factory=dict)

    scan_time_ms: int = 0


class MapScanner:
    """Orchestrates the full map scan pipeline."""

    def __init__(self):
        self.framework_detector = FrameworkDetector()
        self.route_extractor = RouteExtractor()
        self.entity_mapper = EntityMapper()
        self.service_mapper = ServiceMapper()
        self.capability_inferrer = CapabilityInferrer()
        self.frontend_extractor = FrontendExtractor()
        self.cross_layer_linker = CrossLayerLinker()

    def scan(self, path: str | Path, deep: bool = False) -> MapResult:
        """Execute the full map scan pipeline."""
        import time
        start = time.time()

        path = Path(path)

        # Layer 1: Backend framework detection
        framework_result = self.framework_detector.detect(path)
        backend_framework = framework_result.get("detected")
        backend_confidence = framework_result.get("confidence", 0)

        # Layer 2: Route extraction
        routes = []
        if backend_framework:
            extracted_routes = self.route_extractor.extract(path, backend_framework)
            routes = [self._route_to_dict(r) for r in extracted_routes]

        # Layer 3: Entity mapping
        entities = []
        extracted_entities = self.entity_mapper.map(path)
        entities = [self._entity_to_dict(e) for e in extracted_entities]

        # Layer 4: Service mapping
        services = []
        extracted_services = self.service_mapper.map(path)
        services = [self._service_to_dict(s) for s in extracted_services]

        # Layer 5: Capability inference
        capability_candidates = []
        if routes or services:
            extracted_routes = [self._dict_to_route(r) for r in routes] if routes else []
            caps = self.capability_inferrer.infer(
                extracted_routes,
                extracted_entities,
                extracted_services,
            )
            capability_candidates = [self._cap_to_dict(c) for c in caps]

        # Layer 6: Workflow inference (deep mode enables richer pattern matching)
        workflow_candidates = self._infer_workflows(routes, capability_candidates, deep=deep)

        # Layer 7: Frontend extraction
        frontend_result = self.frontend_extractor.extract(path)
        frontend_framework = frontend_result.get("framework")
        pages = frontend_result.get("pages", [])
        components = frontend_result.get("components", [])
        frontend_api_calls = frontend_result.get("api_calls", [])

        # Layer 8: Cross-layer linking
        cross_links = 0
        link_high = 0
        link_medium = 0
        graph = None

        if frontend_api_calls:
            from dataclasses import asdict
            br = asdict(MapResult(
                backend_framework=backend_framework,
                backend_confidence=backend_confidence,
                routes=routes,
                entities=entities,
                services=services,
                capability_candidates=capability_candidates,
            ))
            # Use simple dict for linker
            br["framework"] = backend_framework
            br["confidence"] = backend_confidence
            graph, link_result = self.cross_layer_linker.link(br, frontend_result)
            cross_links = link_result.total_links
            link_high = link_result.high_confidence
            link_medium = link_result.medium_confidence

        # Summaries
        risk_summary = self._summarize_risk(capability_candidates)
        family_summary = self._summarize_families(capability_candidates)

        scan_time_ms = int((time.time() - start) * 1000)

        return MapResult(
            backend_framework=backend_framework,
            backend_confidence=backend_confidence,
            frontend_framework=frontend_framework,
            routes=routes,
            entities=entities,
            services=services,
            pages=pages,
            components=components,
            frontend_api_calls=frontend_api_calls,
            capability_candidates=capability_candidates,
            workflow_candidates=workflow_candidates,
            cross_links=cross_links,
            link_confidence_high=link_high,
            link_confidence_medium=link_medium,
            risk_summary=risk_summary,
            family_summary=family_summary,
            scan_time_ms=scan_time_ms,
        )

    def _route_to_dict(self, route: ExtractedRoute) -> dict:
        return {
            "path": route.path,
            "method": route.method,
            "function": route.function_name,
            "file": route.file_path,
            "params": route.params,
        }

    def _entity_to_dict(self, entity: ExtractedEntity) -> dict:
        return {
            "name": entity.name,
            "table": entity.table_name,
            "file": entity.file_path,
            "fields": entity.fields,
        }

    def _service_to_dict(self, service: ExtractedService) -> dict:
        return {
            "name": service.name,
            "file": service.file_path,
            "methods": service.methods,
            "verbs": service.domain_verbs,
        }

    def _cap_to_dict(self, cap: CapabilityCandidate) -> dict:
        return {
            "name": cap.name,
            "description": cap.description,
            "kind": cap.kind,
            "family": cap.family,
            "side_effect": cap.side_effect_level,
            "risk": cap.risk_level,
            "approval_required": cap.approval_required,
        }

    def _dict_to_route(self, d: dict) -> ExtractedRoute:
        return ExtractedRoute(
            path=d.get("path", "/"),
            method=d.get("method", "get"),
            function_name=d.get("function", ""),
            file_path=d.get("file", ""),
        )

    def _infer_workflows(self, routes: list[dict], capabilities: list[dict], deep: bool = False) -> list[dict]:
        """Simple workflow inference from route patterns.
        
        When deep=True, uses extended pattern set for richer inference.
        """
        workflows = []

        # Common workflow patterns
        patterns = [
            {"name": "create_order_flow", "steps": ["create", "get"]},
            {"name": "payment_flow", "steps": ["create", "get", "update"]},
            {"name": "user_onboarding", "steps": ["create", "get"]},
        ]

        # Deep mode: add more workflow patterns
        if deep:
            patterns.extend([
                {"name": "crud_lifecycle", "steps": ["create", "get", "update", "delete"]},
                {"name": "approval_flow", "steps": ["create", "get", "approve"]},
                {"name": "review_flow", "steps": ["create", "get", "review", "update"]},
                {"name": "search_flow", "steps": ["list", "get"]},
                {"name": "auth_flow", "steps": ["create", "authenticate", "verify"]},
            ])

        # Match patterns to actual capabilities
        for pattern in patterns:
            matched_steps = []
            for step in pattern["steps"]:
                for cap in capabilities:
                    if step in cap.get("name", ""):
                        matched_steps.append(cap["name"])
                        break

            if len(matched_steps) >= 2:
                workflows.append({
                    "name": pattern["name"],
                    "steps": matched_steps,
                    "inferred": True,
                })

        return workflows

    def _summarize_risk(self, capabilities: list[dict]) -> dict[str, int]:
        summary = {"low": 0, "medium": 0, "high": 0}
        for cap in capabilities:
            risk = cap.get("risk", "low")
            if risk in summary:
                summary[risk] += 1
        return summary

    def _summarize_families(self, capabilities: list[dict]) -> dict[str, int]:
        summary = {}
        for cap in capabilities:
            family = cap.get("family", "unknown")
            summary[family] = summary.get(family, 0) + 1
        return summary

    def to_envelope(self, result: MapResult) -> dict[str, Any]:
        """Convert result to ToolResultEnvelope format."""
        return {
            "ok": True,
            "tool": "map.scan",
            "status": "completed",
            "summary": f"Scanned {result.backend_framework or 'unknown'} backend, {result.frontend_framework or 'no'} frontend: {len(result.routes)} routes, {len(result.pages)} pages, {len(result.capability_candidates)} capabilities, {result.cross_links} cross-links",
            "result": {
                "backend_framework": result.backend_framework,
                "backend_confidence": result.backend_confidence,
                "frontend_framework": result.frontend_framework,
                "routes": result.routes,
                "entities": result.entities,
                "services": result.services,
                "pages": result.pages,
                "components": result.components,
                "frontend_api_calls": result.frontend_api_calls,
                "capabilities": result.capability_candidates,
                "workflows": result.workflow_candidates,
                "cross_links": result.cross_links,
                "link_confidence_high": result.link_confidence_high,
                "link_confidence_medium": result.link_confidence_medium,
                "risk_summary": result.risk_summary,
                "family_summary": result.family_summary,
            },
            "next": {
                "actions": [
                    "map.capabilities",
                    "map.workflows",
                    "map.graph",
                    "map.trace",
                ],
                "hints": [
                    f"Found {result.risk_summary.get('high', 0)} high-risk capabilities",
                    f"Linked {result.cross_links} frontend-backend connections",
                    "Use 'aicp map trace' to explore full-stack paths",
                ],
            },
            "risk": {
                "level": "low",
                "approval_required": False,
            },
            "metadata": {
                "scan_time_ms": result.scan_time_ms,
            },
        }
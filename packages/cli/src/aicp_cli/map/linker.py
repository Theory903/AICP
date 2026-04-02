"""Cross-layer linker - connects frontend to backend through evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aicp_cli.map.graph import CodebaseGraph, Node, Edge, NodeType, EdgeType, make_node_id


@dataclass
class LinkResult:
    """Result of linking frontend to backend."""

    total_links: int
    high_confidence: int
    medium_confidence: int
    unmatched_frontend: list[dict]
    unmatched_backend: list[dict]


class CrossLayerLinker:
    """Links frontend artifacts to backend through evidence."""

    def link(
        self,
        backend_result: dict[str, Any],
        frontend_result: dict[str, Any],
    ) -> tuple[CodebaseGraph, LinkResult]:
        """Link frontend and backend into a unified graph."""
        graph = CodebaseGraph()
        graph.metadata = {
            "backend_framework": backend_result.get("framework"),
            "frontend_framework": frontend_result.get("framework"),
        }

        # Add backend nodes
        self._add_backend_nodes(graph, backend_result)

        # Add frontend nodes
        self._add_frontend_nodes(graph, frontend_result)

        # Create links
        link_result = self._create_links(graph, backend_result, frontend_result)

        return graph, link_result

    def _add_backend_nodes(self, graph: CodebaseGraph, result: dict[str, Any]) -> None:
        """Add backend nodes to graph."""
        # Framework node
        framework = result.get("framework")
        if framework:
            node = Node(
                id=make_node_id(NodeType.FRAMEWORK, framework),
                type=NodeType.FRAMEWORK,
                label=framework,
                properties={"confidence": result.get("confidence", 0)},
            )
            graph.add_node(node)

        # Route nodes
        routes = result.get("routes", [])
        for route in routes:
            node_id = make_node_id(NodeType.ROUTE, f"{route.get('method', 'GET')}_{route.get('path', '/')}")
            node = Node(
                id=node_id,
                type=NodeType.ROUTE,
                label=f"{route.get('method', 'GET')} {route.get('path', '/')}",
                file_path=route.get("file"),
                properties={"method": route.get("method"), "path": route.get("path")},
            )
            graph.add_node(node)

        # Entity nodes
        entities = result.get("entities", [])
        for entity in entities:
            node_id = make_node_id(NodeType.ENTITY, entity.get("name", "unknown"))
            node = Node(
                id=node_id,
                type=NodeType.ENTITY,
                label=entity.get("name", "unknown"),
                file_path=entity.get("file"),
                properties={"table": entity.get("table")},
            )
            graph.add_node(node)

        # Service nodes
        services = result.get("services", [])
        for service in services:
            node_id = make_node_id(NodeType.SERVICE, service.get("name", "unknown"))
            node = Node(
                id=node_id,
                type=NodeType.SERVICE,
                label=service.get("name", "unknown"),
                file_path=service.get("file"),
                properties={"methods": service.get("methods", [])},
            )
            graph.add_node(node)

        # Capability nodes
        caps = result.get("capability_candidates", [])
        for cap in caps:
            node_id = make_node_id(NodeType.CAPABILITY, cap.get("name", "unknown"))
            node = Node(
                id=node_id,
                type=NodeType.CAPABILITY,
                label=cap.get("name", "unknown"),
                properties={
                    "kind": cap.get("kind"),
                    "family": cap.get("family"),
                    "risk": cap.get("risk"),
                    "side_effect": cap.get("side_effect"),
                },
            )
            graph.add_node(node)

    def _add_frontend_nodes(self, graph: CodebaseGraph, result: dict[str, Any]) -> None:
        """Add frontend nodes to graph."""
        # Framework node
        if result.get("framework"):
            node_id = make_node_id(NodeType.FRAMEWORK, f"frontend_{result['framework']}")
            node = Node(
                id=node_id,
                type=NodeType.FRAMEWORK,
                label=f"frontend: {result['framework']}",
                properties={"type": "frontend"},
            )
            graph.add_node(node)

        # Page nodes
        for page in result.get("pages", []):
            node_id = make_node_id(NodeType.PAGE, page.get("path", "/"))
            node = Node(
                id=node_id,
                type=NodeType.PAGE,
                label=page.get("path", "/"),
                file_path=page.get("file"),
                properties={"page_type": page.get("type")},
            )
            graph.add_node(node)

        # API call nodes
        for call in result.get("api_calls", []):
            node_id = make_node_id(NodeType.API_CALL, f"{call.get('method', 'GET')}_{call.get('path', '/')}")
            node = Node(
                id=node_id,
                type=NodeType.API_CALL,
                label=f"{call.get('method', 'GET')} {call.get('path', '/')}",
                file_path=call.get("file"),
                properties={"method": call.get("method"), "path": call.get("path")},
            )
            graph.add_node(node)

    def _create_links(
        self,
        graph: CodebaseGraph,
        backend_result: dict[str, Any],
        frontend_result: dict[str, Any],
    ) -> LinkResult:
        """Create edges between frontend and backend."""
        total_links = 0
        high_conf = 0
        medium_conf = 0
        unmatched_fe = []
        unmatched_be = []

        # Build backend route lookup
        backend_routes = {}
        for route in backend_result.get("routes", []):
            key = f"{route.get('method', 'GET').upper()}_{route.get('path', '/').lower()}"
            backend_routes[key] = route

        # Link API calls to backend routes
        for call in frontend_result.get("api_calls", []):
            call_key = f"{call.get('method', 'GET').upper()}_{call.get('path', '/').lower()}"

            # Try exact match first
            route = backend_routes.get(call_key)

            # Try fuzzy match
            if not route:
                for bk, br in backend_routes.items():
                    if call.get("path", "").lower() in bk or bk.split("_", 1)[-1] in call.get("path", "").lower():
                        route = br
                        break

            if route:
                call_node_id = make_node_id(NodeType.API_CALL, f"{call.get('method', 'GET')}_{call.get('path', '/')}")
                route_node_id = make_node_id(NodeType.ROUTE, f"{route.get('method', 'GET')}_{route.get('path', '/')}")

                route_key = f"{route.get('method', 'GET').upper()}_{route.get('path', '/').lower()}"
                confidence = 1.0 if call_key == route_key else 0.7

                edge = Edge(
                    source_id=call_node_id,
                    target_id=route_node_id,
                    type=EdgeType.SUBMITS_TO,
                    evidence=[f"{call.get('file', '')} -> {route.get('file', '')}"],
                    confidence=confidence,
                )
                graph.add_edge(edge)
                total_links += 1
                if confidence >= 0.8:
                    high_conf += 1
                else:
                    medium_conf += 1
            else:
                unmatched_fe.append(call)

        # Track unmatched backend routes
        matched_backend = set()
        for edge in graph.edges:
            if edge.type == EdgeType.SUBMITS_TO:
                matched_backend.add(edge.target_id)

        for route in backend_result.get("routes", []):
            route_node_id = make_node_id(NodeType.ROUTE, f"{route.get('method', 'GET')}_{route.get('path', '/')}")
            if route_node_id not in matched_backend:
                unmatched_be.append(route)

        return LinkResult(
            total_links=total_links,
            high_confidence=high_conf,
            medium_confidence=medium_conf,
            unmatched_frontend=unmatched_fe,
            unmatched_backend=unmatched_be,
        )

    def trace_path(
        self,
        graph: CodebaseGraph,
        from_node: str,
        to_type: NodeType,
    ) -> list[dict]:
        """Trace path from a node to a target type."""
        paths = graph.trace_path(from_node, to_type)

        result = []
        for path in paths:
            path_dict = []
            for node in path:
                path_dict.append({
                    "id": node.id,
                    "type": node.type.value,
                    "label": node.label,
                    "file": node.file_path,
                })
            result.append(path_dict)

        return result
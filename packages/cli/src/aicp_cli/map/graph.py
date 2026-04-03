"""Graph model for full-stack codebase mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Types of nodes in the codebase graph."""

    FRAMEWORK = "framework"
    ROUTE = "route"
    HANDLER = "handler"
    SERVICE = "service"
    ENTITY = "entity"
    EXTERNAL = "external"
    PAGE = "page"
    COMPONENT = "component"
    UI_ACTION = "ui_action"
    API_CALL = "api_call"
    CAPABILITY = "capability"
    WORKFLOW = "workflow"
    RISK = "risk"


class EdgeType(str, Enum):
    """Types of edges in the codebase graph."""

    CALLS = "calls"
    RENDERS = "renders"
    SUBMITS_TO = "submits_to"
    MUTATES = "mutates"
    READS = "reads"
    TRIGGERS = "triggers"
    BELONGS_TO = "belongs_to"
    CONTINUES_AS = "continues_as"
    REQUIRES_APPROVAL = "requires_approval"
    HAS_RISK = "has_risk"
    LINKS_TO = "links_to"


@dataclass
class Node:
    """A node in the codebase graph."""

    id: str
    type: NodeType
    label: str

    properties: dict[str, Any] = field(default_factory=dict)

    file_path: str | None = None
    line_number: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
            "file": self.file_path,
            "line": self.line_number,
            "metadata": self.metadata,
        }


@dataclass
class Edge:
    """An edge in the codebase graph."""

    source_id: str
    target_id: str
    type: EdgeType

    evidence: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.type.value,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class CodebaseGraph:
    """Full-stack codebase mapping graph."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_outgoing(
        self, node_id: str, edge_type: EdgeType | None = None
    ) -> list[Node]:
        """Get nodes connected from a node."""
        result = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge_type is None or edge.type == edge_type:
                    target = self.nodes.get(edge.target_id)
                    if target:
                        result.append(target)
        return result

    def get_incoming(
        self, node_id: str, edge_type: EdgeType | None = None
    ) -> list[Node]:
        """Get nodes connecting to a node."""
        result = []
        for edge in self.edges:
            if edge.target_id == node_id:
                if edge_type is None or edge.type == edge_type:
                    source = self.nodes.get(edge.source_id)
                    if source:
                        result.append(source)
        return result

    def find_by_type(self, node_type: NodeType) -> list[Node]:
        """Find all nodes of a given type."""
        return [n for n in self.nodes.values() if n.type == node_type]

    def find_by_label(self, label: str) -> list[Node]:
        """Find nodes by label (partial match)."""
        label_lower = label.lower()
        return [n for n in self.nodes.values() if label_lower in n.label.lower()]

    def trace_path(self, start_id: str, end_type: NodeType) -> list[list[Node]]:
        """Find all paths from start node to end type."""
        paths = []

        def dfs(current_id: str, visited: set[str], path: list[Node]):
            if current_id in visited:
                return

            node = self.nodes.get(current_id)
            if not node:
                return

            visited.add(current_id)
            path.append(node)

            if node.type == end_type:
                paths.append(list(path))
            else:
                for next_node in self.get_outgoing(current_id):
                    dfs(next_node.id, visited, path)

            path.pop()
            visited.remove(current_id)

        dfs(start_id, set(), [])
        return paths

    def to_dict(self) -> dict:
        """Export graph as dictionary."""
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }


def make_node_id(node_type: NodeType, name: str) -> str:
    """Generate a consistent node ID."""
    clean_name = name.replace("/", "_").replace(".", "_").replace(":", "_")
    return f"{node_type.value}:{clean_name}"

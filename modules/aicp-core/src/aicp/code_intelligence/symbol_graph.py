
import networkx as nx

from .models import ASTNode, CallEdge, SymbolLocation


class SymbolGraph:
    def __init__(self):
        self._graph = nx.DiGraph()
        self._nodes: dict[str, ASTNode] = {}

    def add_node(self, node: ASTNode):
        self._nodes[node.id] = node
        self._graph.add_node(node.id, **node.model_dump())
        if node.parent_id:
            self.add_relation(node.parent_id, node.id, "contains")

    def add_symbol(self, node: ASTNode):
        self.add_node(node)

    def add_relation(self, source_id: str, target_id: str, relation_type: str):
        self._graph.add_edge(source_id, target_id, relation_type=relation_type)

    def add_call_edge(self, edge: CallEdge):
        self.add_relation(edge.caller_id, edge.callee_id, "calls")
        self._graph.nodes[edge.callee_id]["call_site"] = edge.call_site.model_dump()

    def get_definitions(self, name: str) -> list[ASTNode]:
        return [node for node in self._nodes.values() if node.name == name]

    def get_node(self, node_id: str) -> ASTNode | None:
        return self._nodes.get(node_id)

    def find_references(self, node_id: str) -> list[str]:
        # Simple graph-based reference finding
        return [source for source, target, data in self._graph.in_edges(node_id, data=True)
                if data.get("relation_type") == "references"]

    def find_calls(self, node_id: str) -> list[str]:
        return [target for source, target, data in self._graph.out_edges(node_id, data=True)
                if data.get("relation_type") == "calls"]

    def get_callers(self, node_id: str) -> list[str]:
        return [source for source, target, data in self._graph.in_edges(node_id, data=True)
                if data.get("relation_type") == "calls"]

    def get_callees(self, node_id: str) -> list[str]:
        return [target for source, target, data in self._graph.out_edges(node_id, data=True)
                if data.get("relation_type") == "calls"]

    def get_references(self, node_id: str) -> list[SymbolLocation]:
        refs: list[SymbolLocation] = []
        for _source, target, data in self._graph.in_edges(node_id, data=True):
            if data.get("relation_type") != "calls":
                continue
            call_site = self._graph.nodes[target].get("call_site")
            if call_site:
                refs.append(SymbolLocation(**call_site))
        return refs

    def get_neighbors(self, node_id: str) -> list[str]:
        return list(self._graph.neighbors(node_id))

    def clear(self):
        self._graph.clear()
        self._nodes.clear()

from pathlib import Path
from typing import Any, Dict, List, Optional
from .ast_indexer import ASTIndexer
from .symbol_graph import SymbolGraph
from .models import ASTNode, SymbolKind

class CodeContext:
    def __init__(self, graph: Optional[SymbolGraph] = None, token_budget: int = 8000):
        self._indexer = ASTIndexer()
        self._graph = graph or SymbolGraph()
        self._token_budget = token_budget
        self._indexed_files: set[str] = set()

    def index_directory(self, root_dir: str):
        path = Path(root_dir)
        for py_file in path.rglob("*.py"):
            self.index_file(str(py_file))

    def index_file(self, file_path: str):
        if file_path in self._indexed_files:
            return
            
        nodes = self._indexer.index_file(file_path)
        for node in nodes:
            self._graph.add_node(node)
        self._indexed_files.add(file_path)

    def find_symbol(self, name: str, kind: Optional[SymbolKind] = None) -> List[ASTNode]:
        results = []
        for node in self._graph._nodes.values():
            if node.name == name:
                if kind is None or node.kind == kind:
                    results.append(node)
        return results

    def get_references(self, node_id: str) -> List[ASTNode]:
        ref_ids = self._graph.find_references(node_id)
        refs: List[ASTNode] = []
        for ref_id in ref_ids:
            node = self._graph.get_node(ref_id)
            if node:
                refs.append(node)
        return refs

    def get_calls(self, node_id: str) -> List[ASTNode]:
        call_ids = self._graph.find_calls(node_id)
        calls: List[ASTNode] = []
        for call_id in call_ids:
            node = self._graph.get_node(call_id)
            if node:
                calls.append(node)
        return calls

    def get_file_symbols(self, file_path: str) -> List[ASTNode]:
        return [node for node in self._graph._nodes.values() if node.location.uri == file_path]

    def build_context(self, focus_uris: List[str], depth: int = 2) -> "CodeContext":
        for uri in focus_uris:
            self.index_file(uri)
        return self


CodeContextBuilder = CodeContext

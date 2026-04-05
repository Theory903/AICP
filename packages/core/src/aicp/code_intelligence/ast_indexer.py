import ast
from pathlib import Path
from typing import Optional, Any
from .models import ASTNode, SymbolLocation, SymbolKind

class ASTIndexer:
    def __init__(self):
        self._cache: dict[str, list[ASTNode]] = {}

    def index_file(self, file_path: str) -> list[ASTNode]:
        path = Path(file_path)
        if not path.exists() or path.suffix != ".py":
            return []
        
        try:
            with open(path, "r") as f:
                source = f.read()
            tree = ast.parse(source)
            nodes = self._process_node(tree, file_path)
            self._cache[file_path] = nodes
            return nodes
        except Exception:
            return []

    def _process_node(self, node: ast.AST, file_path: str, parent_id: Optional[str] = None) -> list[ASTNode]:
        nodes = []
        current_node = None
        
        if isinstance(node, ast.Module):
            kind = SymbolKind.MODULE
            name = Path(file_path).stem
        elif isinstance(node, ast.ClassDef):
            kind = SymbolKind.CLASS
            name = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = SymbolKind.FUNCTION
            name = node.name
        elif isinstance(node, ast.Assign):
            kind = SymbolKind.VARIABLE
            name = self._get_assign_name(node)
        else:
            kind = None
            name = None

        if kind and name is not None:
            lineno = getattr(node, "lineno", 1)
            col_offset = getattr(node, "col_offset", 0)
            end_lineno = getattr(node, "end_lineno", None)
            end_col_offset = getattr(node, "end_col_offset", None)
            
            properties: dict[str, Any] = {}
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                properties["args"] = [arg.arg for arg in node.args.args]
                properties["async"] = isinstance(node, ast.AsyncFunctionDef)
            if isinstance(node, ast.ClassDef):
                properties["bases"] = [self._get_name(base) for base in node.bases]

            current_node = ASTNode(
                kind=kind,
                name=name,
                location=SymbolLocation(
                    uri=file_path,
                    line=lineno,
                    character=col_offset,
                    end_line=end_lineno,
                    end_character=end_col_offset
                ),
                parent_id=parent_id,
                properties=properties
            )
            nodes.append(current_node)
            parent_id = current_node.id

        for child in ast.iter_child_nodes(node):
            child_nodes = self._process_node(child, file_path, parent_id)
            if child_nodes and current_node:
                current_node.children.append(child_nodes[0].id)
            nodes.extend(child_nodes)
            
        return nodes

    def _get_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "Unknown"

    def _get_assign_name(self, node: ast.Assign) -> Optional[str]:
        if node.targets and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
        return None

    def invalidate(self, file_path: str):
        if file_path in self._cache:
            del self._cache[file_path]

"""Entity mapper - detects entities from models/ORM code."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedEntity:
    """An extracted database entity."""

    name: str
    table_name: str
    file_path: str
    fields: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    status_enum: list[str] | None = None


class EntityMapper:
    """Maps database entities from ORM models."""

    def map(self, path: str | Path) -> list[ExtractedEntity]:
        """Map entities from the codebase."""
        path = Path(path)
        entities = []

        for py_file in path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            entities.extend(self._extract_from_file(py_file))

        return entities

    def _should_skip(self, f: Path) -> bool:
        skip_dirs = {"node_modules", ".venv", "venv", "__pycache__", ".git", "tests"}
        return any(skip in str(f) for skip in skip_dirs)

    def _extract_from_file(self, file_path: Path) -> list[ExtractedEntity]:
        entities = []
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity = self._extract_entity(node, str(file_path))
                    if entity:
                        entities.append(entity)
        except Exception:
            pass
        return entities

    def _extract_entity(self, node: ast.ClassDef, file_path: str) -> ExtractedEntity | None:
        name = node.name

        # Check for SQLAlchemy model
        is_model = False
        table_name = name.lower()

        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ["Model", "Base"]:
                    is_model = True
            elif isinstance(base, ast.Attribute):
                if base.attr in ["Model", "Base"]:
                    is_model = True

        # Look for table name
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__tablename__":
                            if isinstance(item.value, ast.Constant):
                                table_name = item.value.value

        if not is_model:
            return None

        # Extract fields
        fields = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_info = {"name": target.id, "type": "any"}
                        if isinstance(item.value, ast.Call):
                            if hasattr(item.value.func, "id"):
                                field_info["type"] = item.value.func.id
                            elif hasattr(item.value.func, "attr"):
                                field_info["type"] = item.value.func.attr
                        fields.append(field_info)
            elif isinstance(item, ast.FunctionDef):
                # Check for relationship
                if any("relationship" in ast.unparse(d) for d in item.decorator_list if isinstance(d, ast.Call)):
                    pass

        return ExtractedEntity(
            name=name,
            table_name=table_name,
            file_path=file_path,
            fields=fields,
        )
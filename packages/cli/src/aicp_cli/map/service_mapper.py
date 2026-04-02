"""Service mapper - maps business logic services."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedService:
    """An extracted service/business logic."""

    name: str
    file_path: str
    methods: list[str] = field(default_factory=list)
    domain_verbs: list[str] = field(default_factory=list)


class ServiceMapper:
    """Maps services and business logic."""

    ACTION_VERBS = {
        "create", "update", "delete", "remove", "add", "edit", "modify",
        "get", "fetch", "retrieve", "list", "search", "query",
        "send", "notify", "publish", "emit",
        "process", "execute", "run", "handle",
        "authenticate", "authorize", "validate", "verify",
        "approve", "reject", "confirm", "cancel",
        "transfer", "pay", "refund", "charge",
    }

    def map(self, path: str | Path) -> list[ExtractedService]:
        """Map services from the codebase."""
        path = Path(path)
        services = []

        for py_file in path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            found = self._extract_services(py_file)
            services.extend(found)

        return services

    def _should_skip(self, f: Path) -> bool:
        skip_dirs = {"node_modules", ".venv", "venv", "__pycache__", ".git", "tests"}
        return any(skip in str(f) for skip in skip_dirs)

    def _extract_services(self, file_path: Path) -> list[ExtractedService]:
        """Extract all service classes from a file."""
        results = []
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for service-like class
                    if self._is_service_class(node):
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        domain_verbs = self._extract_domain_verbs(methods)

                        results.append(ExtractedService(
                            name=node.name,
                            file_path=str(file_path),
                            methods=methods,
                            domain_verbs=domain_verbs,
                        ))
        except Exception:
            pass
        return results

    def _is_service_class(self, node: ast.ClassDef) -> bool:
        """Check if class looks like a service."""
        name = node.name.lower()
        # Common service naming patterns
        if "service" in name or "manager" in name or "handler" in name:
            return True
        if "controller" in name or "router" in name:
            return True
        return False

    def _extract_domain_verbs(self, methods: list[str]) -> list[str]:
        """Extract domain verbs from method names."""
        verbs = []
        for method in methods:
            parts = re.split(r"[_-]", method.lower())
            for part in parts:
                if part in self.ACTION_VERBS:
                    verbs.append(part)
        return list(set(verbs))
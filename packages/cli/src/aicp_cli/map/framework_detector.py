"""Framework detector - detects backend framework type."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class FrameworkDetector:
    """Detects the framework type of a backend application."""

    FRAMEWORKS = {
        "fastapi": {
            "indicators": ["fastapi", "FastAPI"],
            "files": ["main.py", "app.py"],
            "imports": ["from fastapi import", "import fastapi"],
            "markers": ["app = FastAPI()", "@app.get", "@app.post"],
        },
        "express": {
            "indicators": ["express", "Express"],
            "files": ["server.js", "index.js", "app.js"],
            "imports": ["require('express')", "from 'express'"],
            "markers": ["express()", "app.get(", "app.post("],
        },
        "flask": {
            "indicators": ["flask", "Flask"],
            "files": ["app.py", "main.py"],
            "imports": ["from flask import", "import flask"],
            "markers": ["app = Flask(", "@app.route"],
        },
        "django": {
            "indicators": ["django", "Django"],
            "files": ["manage.py", "settings.py"],
            "imports": ["from django", "import django"],
            "markers": ["urlpatterns", "INSTALLED_APPS"],
        },
        "nestjs": {
            "indicators": ["@nestjs", "nestjs", "NestJS"],
            "files": ["main.ts", "app.module.ts"],
            "imports": ["@nestjs/common", "@nestjs/core"],
            "markers": ["@Controller", "@Injectable", "@Get("],
        },
        "springboot": {
            "indicators": ["spring", "Spring"],
            "files": ["pom.xml", "build.gradle"],
            "imports": ["org.springframework", "@SpringBootApplication"],
            "markers": ["@RestController", "@Service", "@Autowired"],
        },
        "rails": {
            "indicators": ["rails", "Rails"],
            "files": ["config/routes.rb", "Gemfile"],
            "imports": ["class ApplicationRecord"],
            "markers": ["resources :", "get '", "post '"],
        },
    }

    def detect(self, path: str | Path) -> dict[str, Any]:
        """Detect framework from codebase path."""
        path = Path(path)
        results = {"detected": None, "confidence": 0.0, "signals": []}

        for framework, indicators in self.FRAMEWORKS.items():
            score = 0
            signals = []

            # Check package.json for Node frameworks
            pkg_json = path / "package.json"
            if pkg_json.exists():
                content = pkg_json.read_text()
                for ind in indicators.get("indicators", []):
                    if ind in content:
                        score += 2
                        signals.append(f"package.json: {ind}")

            # Check pyproject.toml / requirements.txt for Python
            pyproject = path / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                for ind in indicators.get("indicators", []):
                    if ind in content:
                        score += 2
                        signals.append(f"pyproject.toml: {ind}")

            reqs = path / "requirements.txt"
            if reqs.exists():
                content = reqs.read_text()
                for ind in indicators.get("indicators", []):
                    if ind.lower() in content.lower():
                        score += 1
                        signals.append(f"requirements.txt: {ind}")

            # Check key files
            for f in indicators.get("files", []):
                if (path / f).exists():
                    score += 3
                    signals.append(f"file: {f}")

            # Check imports in .py files
            for py_file in path.rglob("*.py"):
                if "node_modules" in str(py_file) or ".venv" in str(py_file):
                    continue
                try:
                    content = py_file.read_text()
                    for imp in indicators.get("imports", []):
                        if imp in content:
                            score += 1
                            signals.append(f"import: {imp} in {py_file.name}")
                except Exception:
                    pass

            if score > results["confidence"]:
                results = {
                    "detected": framework,
                    "confidence": score,
                    "signals": signals,
                }

        return results

    def get_extractors(self, framework: str) -> list[str]:
        """Get list of extractors needed for this framework."""
        extractors = {
            "fastapi": ["route_extractor", "service_mapper", "entity_mapper"],
            "flask": ["route_extractor", "service_mapper", "entity_mapper"],
            "express": ["route_extractor", "service_mapper", "entity_mapper"],
            "nestjs": ["route_extractor", "service_mapper", "entity_mapper"],
            "django": ["route_extractor", "service_mapper", "entity_mapper"],
        }
        return extractors.get(framework, ["route_extractor"])

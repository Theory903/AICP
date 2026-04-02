"""Route extractor - extracts endpoints from backend code."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedRoute:
    """An extracted API route."""

    path: str
    method: str
    function_name: str
    file_path: str
    params: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    auth_required: bool = False
    tags: list[str] = field(default_factory=list)
    summary: str = ""


class RouteExtractor:
    """Extracts routes from backend code."""

    def __init__(self):
        self.routes: list[ExtractedRoute] = []

    def extract(self, path: str | Path, framework: str) -> list[ExtractedRoute]:
        """Extract routes from the codebase."""
        path = Path(path)
        self.routes = []

        extractors = {
            "fastapi": self._extract_fastapi,
            "flask": self._extract_flask,
            "express": self._extract_express,
            "nestjs": self._extract_nestjs,
            "django": self._extract_django,
        }

        extractor = extractors.get(framework, self._extract_generic)
        self.routes = extractor(path)

        return self.routes

    def _extract_fastapi(self, path: Path) -> list[ExtractedRoute]:
        """Extract FastAPI routes using regex for reliability."""
        for py_file in path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            self._extract_fastapi_file(py_file)
        return self.routes

    def _should_skip(self, f: Path) -> bool:
        skip_dirs = {"node_modules", ".venv", "venv", "__pycache__", ".git", "tests"}
        return any(skip in str(f) for skip in skip_dirs)

    def _extract_fastapi_file(self, file_path: Path) -> None:
        """Extract routes from a FastAPI Python file using regex."""
        try:
            content = file_path.read_text()
            
            # Match @router.get('/path'), @app.get('/path'), @get('/path')
            patterns = [
                r'@(?:router|app)\.(get|post|put|patch|delete|options|head)\s*\(\s*[\'"]([^\'"#]+)[\'"]',
                r'@get\s*\(\s*[\'"]([^\'"#]+)[\'"]\)',
                r'@post\s*\(\s*[\'"]([^\'"#]+)[\'"]\)',
                r'@put\s*\(\s*[\'"]([^\'"#]+)[\'"]\)',
                r'@patch\s*\(\s*[\'"]([^\'"#]+)[\'"]\)',
                r'@delete\s*\(\s*[\'"]([^\'"#]+)[\'"]\)',
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    if 'router' in pattern or 'app' in pattern:
                        method = match.group(1).lower()
                        path = match.group(2)
                    else:
                        # Extract method name from decorator pattern like r'@get\s*...'
                        m = re.match(r"@(\w+)", pattern)
                        method = m.group(1).lower() if m else "get"
                        path = match.group(1)
                    
                    self.routes.append(ExtractedRoute(
                        path=path,
                        method=method,
                        function_name="",
                        file_path=str(file_path),
                    ))
        except Exception:
            pass

    def _extract_flask(self, path: Path) -> list[ExtractedRoute]:
        """Extract Flask routes."""
        for py_file in path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            try:
                content = py_file.read_text()
                
                # Match @app.route('path'), @route('path')
                pattern = r"@(?:app\.)?route\s*\(\s*['\"]([^'\"]+)['\"]"
                for match in re.finditer(pattern, content):
                    self.routes.append(ExtractedRoute(
                        path=match.group(1),
                        method="get",
                        function_name="",
                        file_path=str(py_file),
                    ))
            except Exception:
                pass
        return self.routes

    def _parse_flask_decorator(self, decorator: Any) -> dict | None:
        """Parse Flask route decorator - not needed with regex."""
        return None

    def _extract_express(self, path: Path) -> list[ExtractedRoute]:
        """Extract Express routes."""
        for js_file in path.rglob("*.js"):
            if "node_modules" in str(js_file):
                continue
            try:
                content = js_file.read_text()
                # Simple regex extraction for common patterns
                routes = self._extract_express_regex(content)
                for route in routes:
                    self.routes.append(ExtractedRoute(
                        path=route["path"],
                        method=route["method"],
                        function_name=route.get("handler", "anonymous"),
                        file_path=str(js_file),
                    ))
            except Exception:
                pass
        return self.routes

    def _extract_express_regex(self, content: str) -> list[dict]:
        """Extract Express routes using regex."""
        routes = []
        # Match app.METHOD('path', handler)
        pattern = r"(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
        for match in re.finditer(pattern, content):
            routes.append({
                "method": match.group(1).lower(),
                "path": match.group(2),
            })
        return routes

    def _extract_nestjs(self, path: Path) -> list[ExtractedRoute]:
        """Extract NestJS routes."""
        for ts_file in path.rglob("*.ts"):
            if "node_modules" in str(ts_file):
                continue
            try:
                content = ts_file.read_text()
                # Extract @Controller and @Get, @Post etc
                controller_match = re.search(r"@Controller\s*\(\s*['\"]([^'\"]+)['\"]", content)
                controller_prefix = controller_match.group(1) if controller_match else ""

                for method in ["get", "post", "put", "patch", "delete"]:
                    pattern = rf"@{method.upper()}\s*\(\s*['\"]([^'\"]*)['\"]"
                    for match in re.finditer(pattern, content):
                        full_path = controller_prefix + match.group(1)
                        self.routes.append(ExtractedRoute(
                            path=full_path or "/",
                            method=method,
                            function_name="",
                            file_path=str(ts_file),
                        ))
            except Exception:
                pass
        return self.routes

    def _extract_django(self, path: Path) -> list[ExtractedRoute]:
        """Extract Django routes."""
        # Look for urls.py files
        for urls_file in path.rglob("urls.py"):
            try:
                content = urls_file.read_text()
                # Extract urlpatterns
                pattern = r"path\s*\(\s*['\"]([^'\"]+)['\"]"
                for match in re.finditer(pattern, content):
                    self.routes.append(ExtractedRoute(
                        path=match.group(1),
                        method="get",
                        function_name="",
                        file_path=str(urls_file),
                    ))
            except Exception:
                pass
        return self.routes

    def _extract_generic(self, path: Path) -> list[ExtractedRoute]:
        """Generic extraction fallback."""
        return []
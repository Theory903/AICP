"""Frontend extractor - extracts pages, components, and API calls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedPage:
    """An extracted frontend page/screen."""

    path: str
    file_path: str
    page_type: str
    title: str = ""
    components: list[str] = field(default_factory=list)
    api_calls: list[dict] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


@dataclass
class ExtractedComponent:
    """An extracted frontend component."""

    name: str
    file_path: str
    props: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


@dataclass
class ExtractedAPICall:
    """An extracted API call."""

    method: str
    path: str
    file_path: str
    handler: str = ""
    caller: str = ""


class FrontendExtractor:
    """Extracts frontend pages, components, and API calls."""

    def extract(self, path: str | Path) -> dict[str, Any]:
        """Extract frontend artifacts from the codebase."""
        path = Path(path)
        result = {
            "framework": None,
            "pages": [],
            "components": [],
            "api_calls": [],
            "routes": [],
        }

        # Detect frontend framework
        result["framework"] = self._detect_framework(path)

        # Extract based on framework
        if result["framework"] in ["nextjs", "react"]:
            result["pages"] = self._extract_react_pages(path)
            result["components"] = self._extract_react_components(path)
            result["api_calls"] = self._extract_api_calls(path)
            result["routes"] = self._extract_react_routes(path)

        return result

    def _detect_framework(self, path: Path) -> str | None:
        """Detect frontend framework."""
        package_json = path / "package.json"
        if package_json.exists():
            content = package_json.read_text()
            if "next" in content:
                return "nextjs"
            if '"react"' in content:
                return "react"
            if "vue" in content:
                return "vue"

        # Check for Next.js app directory
        if (path / "app").exists() or (path / "pages").exists():
            return "nextjs"

        return None

    def _extract_react_pages(self, path: Path) -> list[dict]:
        """Extract React/Next.js pages."""
        pages = []

        # Next.js app directory
        app_dir = path / "app"
        if app_dir.exists():
            pages.extend(self._extract_nextjs_app_dir(app_dir))

        # Next.js pages directory
        pages_dir = path / "pages"
        if pages_dir.exists():
            pages.extend(self._extract_nextjs_pages_dir(pages_dir))

        return pages

    def _extract_nextjs_app_dir(self, app_dir: Path, prefix: str = "") -> list[dict]:
        """Extract Next.js app directory pages."""
        pages = []

        for item in sorted(app_dir.iterdir()):
            if item.name.startswith(".") or item.name.startswith("_"):
                continue

            if item.is_file():
                if item.suffix in [".tsx", ".jsx", ".js", ".ts"]:
                    if item.stem in ["page", "layout", "loading", "error", "not-found"]:
                        continue

                    page_path = f"/{prefix}" if prefix else "/"
                    pages.append({
                        "path": page_path,
                        "file": str(item),
                        "type": self._classify_page(item.stem),
                    })

            elif item.is_dir():
                if item.name == "api":
                    continue
                new_prefix = f"{prefix}/{item.name}" if prefix else item.name
                pages.extend(self._extract_nextjs_app_dir(item, new_prefix))

        return pages

    def _extract_nextjs_pages_dir(self, pages_dir: Path) -> list[dict]:
        """Extract Next.js pages directory pages."""
        pages = []

        for item in pages_dir.rglob("*.tsx"):
            if item.name.startswith("_"):
                continue

            rel = item.relative_to(pages_dir)
            parts = list(rel.parts[:-1])

            if rel.stem == "index":
                path = "/" + "/".join(parts) if parts else "/"
            elif rel.stem == "[...slug]":
                path = "/" + "/".join(parts) + "/*" if parts else "/*"
            elif "[..." in rel.stem:
                path = "/" + "/".join(parts) + "/*" if parts else "/*"
            elif "[" in rel.stem:
                path = "/" + "/".join(parts + [rel.stem.split("[")[0]]) if parts else "/"
            else:
                path = "/" + "/".join(parts + [rel.stem]) if parts else f"/{rel.stem}"

            pages.append({
                "path": path,
                "file": str(item),
                "type": self._classify_page(rel.stem),
            })

        return pages

    def _classify_page(self, name: str) -> str:
        """Classify page type from name."""
        name_lower = name.lower()
        if "dashboard" in name_lower:
            return "dashboard"
        if "login" in name_lower or "signin" in name_lower:
            return "auth"
        if "register" in name_lower or "signup" in name_lower:
            return "auth"
        if "checkout" in name_lower:
            return "checkout"
        if "settings" in name_lower:
            return "settings"
        if "admin" in name_lower:
            return "admin"
        if "detail" in name_lower or name == "[id]":
            return "detail"
        if "list" in name_lower:
            return "list"
        return "page"

    def _extract_react_components(self, path: Path) -> list[dict]:
        """Extract React components."""
        components = []

        for tsx_file in path.rglob("*.tsx"):
            if "node_modules" in str(tsx_file):
                continue

            try:
                content = tsx_file.read_text()

                # Simple class/function component detection
                if "export default" in content or "export const" in content:
                    name = tsx_file.stem
                    components.append({
                        "name": name,
                        "file": str(tsx_file),
                    })
            except Exception:
                pass

        return components

    def _extract_api_calls(self, path: Path) -> list[dict]:
        """Extract API calls from frontend code."""
        api_calls = []

        # Look for fetch, axios, tRPC patterns
        patterns = [
            r"fetch\s*\(\s*['\"]([^'\"]+)['\"]",
            r"axios\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"await\s+(?:use)?(?:fetch|axios)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"\.get\s*\(\s*['\"]([^'\"]+)['\"]",
            r"\.post\s*\(\s*['\"]([^'\"]+)['\"]",
        ]

        for tsx_file in path.rglob("*.tsx"):
            if "node_modules" in str(tsx_file):
                continue

            try:
                content = tsx_file.read_text()
                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        url = match.group(1)
                        if not url.startswith("http"):
                            method = "GET"
                            if "post" in pattern.lower():
                                method = "POST"
                            elif "put" in pattern.lower():
                                method = "PUT"
                            elif "patch" in pattern.lower():
                                method = "PATCH"
                            elif "delete" in pattern.lower():
                                method = "DELETE"

                            api_calls.append({
                                "method": method,
                                "path": url,
                                "file": str(tsx_file),
                            })
            except Exception:
                pass

        return api_calls

    def _extract_react_routes(self, path: Path) -> list[dict]:
        """Extract React Router routes."""
        routes = []

        for tsx_file in path.rglob("*.tsx"):
            if "node_modules" in str(tsx_file):
                continue

            try:
                content = tsx_file.read_text()

                # Route definitions
                patterns = [
                    r"<Route\s+path=['\"]([^'\"]+)['\"]",
                    r"path:\s*['\"]([^'\"]+)['\"]",
                    r"route\s*\(\s*['\"]([^'\"]+)['\"]",
                ]

                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        routes.append({
                            "path": match.group(1),
                            "file": str(tsx_file),
                        })
            except Exception:
                pass

        return routes
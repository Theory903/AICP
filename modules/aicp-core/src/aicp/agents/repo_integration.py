"""Repository Integration Agent - Clone, analyze, and integrate any GitHub repo into AICP."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class Language(Enum):
    """Programming language types."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    UNKNOWN = "unknown"


@dataclass
class AgentCapability:
    """Represents a capability extracted from a repository."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    kind: str = "action"
    file_path: str = ""
    line_number: int = 0
    dependencies: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def to_aicp_capability(self) -> dict[str, Any]:
        """Convert to AICP Capability format."""
        return {
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "tags": self.tags,
        }


@dataclass
class AgentSpec:
    """Agent specification for agent.md generation."""

    name: str
    description: str
    version: str = "1.0.0"
    repository: str = ""
    capabilities: list[AgentCapability] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepoAnalysis:
    """Analysis result of a cloned repository."""

    name: str
    description: str
    language: Language
    main_files: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[AgentCapability] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    readme_content: str = ""
    agent_spec: AgentSpec | None = None


class RepoIntegrationError(Exception):
    """Error during repository integration."""

    pass


class RepoIntegrationAgent:
    """Powerful internal subagent that integrates any GitHub repo into AICP.

    Features:
    - Clone any GitHub repository
    - Analyze and extract capabilities (tools, functions, APIs)
    - Generate agent.md for capability indexing
    - Register capabilities in AICP
    - Integrate with Mammoth shell commands
    """

    def __init__(
        self,
        temp_dir: str | None = None,
        verbose: bool = False,
    ):
        """Initialize the agent.

        Args:
            temp_dir: Temporary directory for cloning repos. Default: system temp.
            verbose: Enable verbose logging.
        """
        self.temp_dir = temp_dir
        self.verbose = verbose
        self._cloned_repos: list[Path] = []

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[RepoIntegrationAgent] {message}")

    def clone_repo(self, repo_url: str, branch: str | None = None) -> Path:
        """Clone a GitHub repository.

        Args:
            repo_url: GitHub repo URL or owner/repo format
            branch: Branch to clone. Default: main/master

        Returns:
            Path to cloned repository

        Raises:
            RepoIntegrationError: If cloning fails
        """
        # Normalize URL
        if "/" in repo_url and not repo_url.startswith("http"):
            repo_url = f"https://github.com/{repo_url}.git"

        # Determine temp directory
        if self.temp_dir:
            base_dir = Path(self.temp_dir)
        else:
            base_dir = Path(tempfile.gettempdir())

        # Extract repo name
        match = re.search(r"/([^/]+?)(?:\.git)?$", repo_url)
        if not match:
            raise RepoIntegrationError(f"Invalid repo URL: {repo_url}")

        repo_name = match.group(1)
        repo_dir = base_dir / repo_name

        # Clean up existing directory
        if repo_dir.exists():
            self._log(f"Removing existing directory: {repo_dir}")
            shutil.rmtree(repo_dir)

        # Clone command
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.append(repo_url)
        cmd.append(str(repo_dir))

        try:
            self._log(f"Cloning {repo_url}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RepoIntegrationError(f"Git clone failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise RepoIntegrationError(f"Git clone timed out for {repo_url}")
        except FileNotFoundError:
            raise RepoIntegrationError("Git not found. Is git installed?")

        self._cloned_repos.append(repo_dir)
        self._log(f"Cloned to {repo_dir}")
        return repo_dir

    def analyze_repo(self, repo_path: Path | str) -> RepoAnalysis:
        """Analyze a cloned repository and extract capabilities.

        Args:
            repo_path: Path to the repository

        Returns:
            RepoAnalysis with extracted capabilities

        Raises:
            RepoIntegrationError: If analysis fails
        """
        repo_path = Path(repo_path)
        if not repo_path.exists():
            raise RepoIntegrationError(f"Repository not found: {repo_path}")

        # Detect language
        language = self._detect_language(repo_path)

        # Get repository name and description
        name = repo_path.name
        description = self._extract_description(repo_path)

        # Find main files
        main_files = self._find_main_files(repo_path, language)

        # Find entry points
        entry_points = self._find_entry_points(repo_path, language)

        # Extract dependencies
        dependencies = self._extract_dependencies(repo_path, language)

        # Extract capabilities based on language
        capabilities = []
        if language == Language.PYTHON:
            capabilities = extract_python_capabilities(repo_path)
        elif language == Language.TYPESCRIPT:
            capabilities = extract_typescript_capabilities(repo_path)

        # Find tools (CLI commands, etc.)
        tools = self._extract_tools(repo_path, language)

        # Find API endpoints
        api_endpoints = self._extract_api_endpoints(repo_path, language)

        # Get README content
        readme_content = self._get_readme(repo_path)

        return RepoAnalysis(
            name=name,
            description=description,
            language=language,
            main_files=main_files,
            entry_points=entry_points,
            dependencies=dependencies,
            capabilities=capabilities,
            tools=tools,
            api_endpoints=api_endpoints,
            readme_content=readme_content,
        )

    def _detect_language(self, repo_path: Path) -> Language:
        """Detect the primary language of the repository."""
        # Check for language-specific files
        if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
            return Language.PYTHON
        if (repo_path / "package.json").exists():
            return Language.TYPESCRIPT
        if (repo_path / "Cargo.toml").exists():
            return Language.RUST
        if (repo_path / "go.mod").exists():
            return Language.GO
        if (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            return Language.JAVA

        # Check for common source files
        if list(repo_path.rglob("*.py")):
            return Language.PYTHON
        if list(repo_path.rglob("*.ts")) or list(repo_path.rglob("*.tsx")):
            return Language.TYPESCRIPT

        return Language.UNKNOWN

    def _extract_description(self, repo_path: Path) -> str:
        """Extract repository description from README or pyproject.toml."""
        # Try README.md first
        readme_paths = ["README.md", "README.rst", "README"]
        for readme_name in readme_paths:
            readme_path = repo_path / readme_name
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8", errors="ignore")
                # Get first non-empty, non-heading line
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line[:200]  # Limit length
                return ""

        # Try pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)

        return ""

    def _find_main_files(self, repo_path: Path, language: Language) -> list[str]:
        """Find main entry files."""
        main_files = []

        if language == Language.PYTHON:
            for pattern in ["__main__.py", "main.py", "app.py", "cli.py"]:
                matches = list(repo_path.rglob(pattern))
                main_files.extend([str(m.relative_to(repo_path)) for m in matches[:3]])

        elif language == Language.TYPESCRIPT:
            for pattern in ["index.ts", "main.ts", "cli.ts"]:
                matches = list(repo_path.rglob(pattern))
                main_files.extend([str(m.relative_to(repo_path)) for m in matches[:3]])

        elif language == Language.RUST:
            for pattern in ["main.rs", "lib.rs"]:
                matches = list(repo_path.rglob(pattern))
                main_files.extend([str(m.relative_to(repo_path)) for m in matches[:3]])

        return main_files[:10]

    def _find_entry_points(self, repo_path: Path, language: Language) -> list[str]:
        """Find entry points (CLI commands, API handlers, etc.)."""
        entry_points = []

        if language == Language.PYTHON:
            # Find CLI entry points
            for py_file in repo_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                # Look for argparse, click, typer
                if "argparse" in content or "click" in content or "typer" in content:
                    entry_points.append(str(py_file.relative_to(repo_path)))

        elif language == Language.TYPESCRIPT:
            # Find package.json bin entries
            pkg_json = repo_path / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    bin_cmds = data.get("bin", {})
                    entry_points.extend(bin_cmds.keys())
                except json.JSONDecodeError:
                    pass

        return entry_points[:10]

    def _extract_dependencies(self, repo_path: Path, language: Language) -> list[str]:
        """Extract dependencies from package manager files."""
        deps = []

        if language == Language.PYTHON:
            for f in ["requirements.txt", "pyproject.toml", "setup.py"]:
                fpath = repo_path / f
                if fpath.exists():
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    # Simple regex for package names
                    matches = re.findall(r'^([a-zA-Z0-9_-]+)', content, re.MULTILINE)
                    deps.extend(matches[:20])

        elif language == Language.TYPESCRIPT:
            pkg_json = repo_path / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    deps = list(all_deps.keys())[:20]
                except json.JSONDecodeError:
                    pass

        return deps

    def _extract_tools(self, repo_path: Path, language: Language) -> list[str]:
        """Extract tools (executable commands, utilities)."""
        tools = []

        if language == Language.PYTHON:
            # Look for function/tool definitions
            for py_file in repo_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                # Look for tool patterns
                if "@tool" in content or "def tool" in content:
                    funcs = re.findall(r'def\s+(\w+)\s*\(', content)
                    tools.extend(funcs)

        elif language == Language.TYPESCRIPT:
            for ts_file in list(repo_path.rglob("*.ts"))[:20]:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
                # Look for exported functions
                exports = re.findall(r'export\s+(?:async\s+)?function\s+(\w+)', content)
                tools.extend(exports)

        return list(set(tools))[:20]

    def _extract_api_endpoints(self, repo_path: Path, language: Language) -> list[dict[str, Any]]:
        """Extract API endpoints."""
        endpoints = []

        if language == Language.PYTHON:
            # Look for FastAPI, Flask, etc.
            for py_file in repo_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # FastAPI routes
                if "@app." in content or "@router." in content:
                    routes = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
                    for method, path in routes:
                        endpoints.append({
                            "method": method.upper(),
                            "path": path,
                            "file": str(py_file.relative_to(repo_path)),
                        })

                # Flask routes
                if "flask" in content.lower():
                    routes = re.findall(r'@(?:app\.| Blueprint\.)?(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
                    for method, path in routes:
                        endpoints.append({
                            "method": method.upper(),
                            "path": path,
                            "file": str(py_file.relative_to(repo_path)),
                        })

        elif language == Language.TYPESCRIPT:
            # Express routes
            for ts_file in repo_path.rglob("*.ts"):
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
                routes = re.findall(r'(?:app|router)\.(get|post|put|delete|patch)\(["\'])([^"\']+)["\']', content)
                for method, _, path in routes:
                    endpoints.append({
                        "method": method.upper(),
                        "path": path,
                        "file": str(ts_file.relative_to(repo_path)),
                    })

        return endpoints[:20]

    def _get_readme(self, repo_path: Path) -> str:
        """Get README content."""
        for name in ["README.md", "README.rst", "README"]:
            readme = repo_path / name
            if readme.exists():
                return readme.read_text(encoding="utf-8", errors="ignore")[:5000]
        return ""

    def create_agent_spec(self, analysis: RepoAnalysis, owner: str = "aicp") -> AgentSpec:
        return AgentSpec(
            name=f"{owner}/{analysis.name}",
            description=analysis.description or f"Agent for {analysis.name}",
            version="1.0.0",
            repository=f"https://github.com/{owner}/{analysis.name}",
            capabilities=analysis.capabilities,
            tools=analysis.tools,
            examples=analysis.readme_content.split("\n")[:5] if analysis.readme_content else [],
            metadata={
                "language": analysis.language.value,
                "generated_at": datetime.now().isoformat(),
                "entry_points": analysis.entry_points,
                "dependencies": analysis.dependencies,
                "api_endpoints": analysis.api_endpoints,
            },
        )

    def generate_agent_md(self, spec: AgentSpec) -> str:
        return create_agent_md(spec)

    def integrate(
        self,
        repo_url: str,
        output_dir: Path | str | None = None,
        register_capabilities: bool = True,
    ) -> AgentSpec:
        """Full integration: clone, analyze, generate agent.md.

        Args:
            repo_url: GitHub repository URL
            output_dir: Directory to save agent.md. Default: ./agents/
            register_capabilities: Whether to register in AICP

        Returns:
            The generated AgentSpec

        Raises:
            RepoIntegrationError: If integration fails
        """
        self._log(f"Integrating {repo_url}...")

        # Clone repo
        repo_path = self.clone_repo(repo_url)

        # Analyze
        analysis = self.analyze_repo(repo_path)
        self._log(f"Found {len(analysis.capabilities)} capabilities")

        # Create spec
        spec = self.create_agent_spec(analysis)

        # Save agent.md
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.cwd() / "agents"

        output_path.mkdir(parents=True, exist_ok=True)
        agent_md_path = output_path / f"{spec.name.replace('/', '_')}.md"

        agent_md_content = self.generate_agent_md(spec)
        agent_md_path.write_text(agent_md_content, encoding="utf-8")
        self._log(f"Saved agent.md to {agent_md_path}")

        # Note: AICP registration would require the runtime
        if register_capabilities:
            self._log("Capability registration ready (runtime required)")
            # In real implementation, this would call AICP API
            # await aicp_client.register_capabilities(spec.capabilities)

        return spec

    def cleanup(self) -> None:
        """Clean up cloned repositories."""
        for repo_dir in self._cloned_repos:
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
                self._log(f"Cleaned up {repo_dir}")
        self._cloned_repos.clear()


def extract_python_capabilities(repo_path: Path) -> list[AgentCapability]:
    """Extract capabilities from Python source files.

    Looks for:
    - Functions with docstrings
    - Classes with methods
    - Tool decorators (@tool, @toolkit)
    - FastAPI/Flask routes
    """
    capabilities = []

    for py_file in repo_path.rglob("*.py"):
        # Skip test files and __pycache__
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        content = py_file.read_text(encoding="utf-8", errors="ignore")

        # Find functions with docstrings
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\):\s*(""".*?""")?'
        for match in re.finditer(func_pattern, content, re.DOTALL):
            func_name = match.group(1)
            params = match.group(2)
            docstring = match.group(3)

            if func_name.startswith("_") or func_name.islower():
                continue

            # Extract description from docstring
            description = ""
            if docstring:
                # Clean up docstring
                docstring = docstring.strip('"""').strip()
                # Get first non-empty line
                for line in docstring.split("\n"):
                    line = line.strip()
                    if line:
                        description = line[:200]
                        break

            # Build input schema from parameters
            input_schema = {"type": "object", "properties": {}, "required": []}
            if params:
                for param in params.split(","):
                    param = param.strip()
                    if param and param != "self":
                        if "=" in param:
                            param_name, default = param.split("=", 1)
                            param_name = param_name.strip()
                        else:
                            param_name = param

                        input_schema["properties"][param_name] = {"type": "any"}

            # Determine capability kind
            kind = "action"
            if "get" in func_name.lower() or "list" in func_name.lower():
                kind = "query"

            capabilities.append(AgentCapability(
                name=f"python.{py_file.stem}.{func_name}",
                description=description or f"Python function: {func_name}",
                input_schema=input_schema,
                kind=kind,
                file_path=str(py_file.relative_to(repo_path)),
            ))

    # Limit to prevent too many capabilities
    return capabilities[:50]


def extract_typescript_capabilities(repo_path: Path) -> list[AgentCapability]:
    """Extract capabilities from TypeScript source files.

    Looks for:
    - Exported functions
    - Exported classes
    - Express/Fastify routes
    - Tool definitions
    """
    capabilities = []

    for ts_file in list(repo_path.rglob("*.ts")) + list(repo_path.rglob("*.tsx")):
        # Skip test files and node_modules
        if "node_modules" in str(ts_file) or "test" in ts_file.name or ".spec." in ts_file.name:
            continue

        content = ts_file.read_text(encoding="utf-8", errors="ignore")

        # Find exported functions
        func_pattern = r'(?:export\s+)(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            params = match.group(2)

            # Build input schema
            input_schema = {"type": "object", "properties": {}}
            if params:
                for param in params.split(","):
                    param = param.strip()
                    if param:
                        # Check for type annotation
                        if ":" in param:
                            param_name, param_type = param.split(":", 1)
                            param_name = param_name.strip()
                            param_type = param_type.strip()
                            input_schema["properties"][param_name] = {"type": param_type}
                        else:
                            input_schema["properties"][param] = {"type": "any"}

            capabilities.append(AgentCapability(
                name=f"ts.{ts_file.stem}.{func_name}",
                description=f"TypeScript function: {func_name}",
                input_schema=input_schema,
                kind="action",
                file_path=str(ts_file.relative_to(repo_path)),
            ))

    return capabilities[:50]


def create_agent_md(spec: AgentSpec) -> str:
    lines = [
        f"# {spec.name}",
        "",
        f"**Version:** {spec.version}",
        f"**Repository:** {spec.repository}",
        "",
        spec.description,
        "",
        "---",
        "",
        "## Capabilities",
        "",
    ]

    if spec.capabilities:
        for cap in spec.capabilities:
            lines.append(f"### {cap.name}")
            lines.append("")
            lines.append(f"{cap.description}")
            lines.append("")
            if cap.input_schema.get("properties"):
                lines.append("**Parameters:**")
                for prop in cap.input_schema["properties"]:
                    lines.append(f"- `{prop}`")
                lines.append("")
    else:
        lines.append("*No explicit capabilities detected.*")
        lines.append("")

    if spec.tools:
        lines.extend([
            "## Tools",
            "",
        ])
        for tool in spec.tools:
            lines.append(f"- `{tool}`")
        lines.append("")

    lines.extend([
        "## Metadata",
        "",
        f"- **Language:** {spec.metadata.get('language', 'unknown')}",
        f"- **Generated:** {spec.metadata.get('generated_at', '')}",
        "",
    ])

    # Add configuration
    if spec.config:
        lines.extend([
            "## Configuration",
            "",
        ])
        for key, value in spec.config.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    return "\n".join(lines)


# Convenience function for quick integration
def integrate_github_repo(
    repo_url: str,
    output_dir: str | None = None,
) -> AgentSpec:
    """Integrate a GitHub repository into AICP.

    This is the main entry point for simple integrations.

    Args:
        repo_url: GitHub repository URL or owner/repo
        output_dir: Directory to save agent.md

    Returns:
        The generated AgentSpec

    Example:
        >>> spec = integrate_github_repo("NousResearch/hermes-agent")
        >>> print(f"Created agent: {spec.name}")
    """
    agent = RepoIntegrationAgent()
    try:
        return agent.integrate(repo_url, output_dir)
    finally:
        agent.cleanup()

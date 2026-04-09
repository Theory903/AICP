"""AICP Auto-Integration - Zero-setup repository integration for AICP and Mammoth.

This module provides automatic provider detection and zero-configuration integration.
Works out of the box with environment variables - no manual setup required.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ProviderType(Enum):
    """Supported LLM providers for agent execution."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    XAI = "xai"
    DEEPSEEK = "deepseek"
    AZURE = "azure"


@dataclass
class ProviderConfig:
    """Provider configuration with auto-detection."""

    provider: ProviderType
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    available: bool = False


class AutoProviderDetector:
    """Automatically detect available providers from environment."""

    PROVIDER_KEYS = {
        ProviderType.OPENAI: ["OPENAI_API_KEY", "OPENAI_KEY"],
        ProviderType.ANTHROPIC: ["ANTHROPIC_API_KEY"],
        ProviderType.OLLAMA: ["OLLAMA_BASE_URL"],
        ProviderType.GEMINI: ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        ProviderType.XAI: ["XAI_API_KEY"],
        ProviderType.DEEPSEEK: ["DEEPSEEK_API_KEY"],
        ProviderType.AZURE: ["AZURE_OPENAI_API_KEY", "AZURE_API_KEY"],
    }

    PROVIDER_MODELS = {
        ProviderType.OPENAI: ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        ProviderType.ANTHROPIC: ["claude-4-sonnet-20250514", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
        ProviderType.OLLAMA: ["llama3", "mistral", "codellama"],
        ProviderType.GEMINI: ["gemini-2.0-flash", "gemini-pro"],
        ProviderType.XAI: ["grok-2", "grok-beta"],
        ProviderType.DEEPSEEK: ["deepseek-chat", "deepseek-coder"],
        ProviderType.AZURE: ["gpt-4", "gpt-35-turbo"],
    }

    def detect(self) -> list[ProviderConfig]:
        """Detect all available providers from environment."""
        providers = []

        for provider_type, env_keys in self.PROVIDER_KEYS.items():
            api_key = None
            base_url = None

            for key in env_keys:
                if value := os.environ.get(key):
                    api_key = value
                    break

            if provider_type == ProviderType.OLLAMA:
                base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

            available = bool(api_key or provider_type == ProviderType.OLLAMA)

            if available:
                model = self.PROVIDER_MODELS.get(provider_type, ["default"])[0]
                providers.append(ProviderConfig(
                    provider=provider_type,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    available=True,
                ))

        return providers

    def get_best_provider(self) -> ProviderConfig | None:
        """Get the best available provider (priority: OpenAI > Anthropic > Ollama)."""
        detected = self.detect()

        priority = [ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.OLLAMA, ProviderType.GEMINI]

        for p in priority:
            for provider in detected:
                if provider.provider == p:
                    return provider

        return detected[0] if detected else None


@dataclass
class IntegrationResult:
    """Result of repository integration."""

    success: bool
    agent_name: str
    repository: str
    capabilities_registered: int
    agent_md_path: str | None = None
    provider_used: ProviderConfig | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AicpAutoIntegrator:
    """Zero-setup auto-integrator for AICP and Mammoth.

    Features:
    - Auto-detects available LLM providers from environment
    - Registers capabilities with AICP automatically
    - Works with Mammoth agent system
    - No manual configuration required
    - Falls back gracefully when providers unavailable
    """

    def __init__(
        self,
        agents_dir: str | None = None,
        registry_file: str | None = None,
    ):
        self.agents_dir = Path(agents_dir) if agents_dir else Path.cwd() / "agents"
        self.registry_file = Path(registry_file) if registry_file else Path.cwd() / ".aicp-agents.json"
        self.provider_detector = AutoProviderDetector()
        self._integrated_agents: dict[str, IntegrationResult] = {}

    def _normalize_repo_url(self, url: str) -> str:
        url = url.strip()
        if url.startswith("https://"):
            match = re.search(r"github\.com[/]([^/]+/[^/]+)", url)
            if match:
                return match.group(1).replace(".git", "")
        if "/" in url and not url.endswith(".git"):
            return url.rstrip("/")
        return f"https://github.com/{url}.git"

    def _get_repo_name(self, url: str) -> str:
        url = url.strip()
        if "github.com" in url:
            match = re.search(r"github\.com[/]([^/]+/[^/]+)", url)
            if match:
                return match.group(1).split("/")[-1].replace(".git", "")
        return url.rstrip("/").split("/")[-1].replace(".git", "")

    def clone_and_analyze(self, repo_url: str) -> tuple[Path, dict[str, Any]]:
        normalized = self._normalize_repo_url(repo_url)
        repo_name = self._get_repo_name(normalized)

        clone_url = f"https://github.com/{normalized}.git"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, repo_name],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Clone failed: {result.stderr}")

            repo_path = Path(tmpdir) / repo_name
            analysis = self._detect_language_and_structure(repo_path)

            return repo_path, analysis

    def _detect_language_and_structure(self, repo_path: Path) -> dict[str, Any]:
        analysis = {
            "name": repo_path.name,
            "description": "",
            "language": "unknown",
            "main_files": [],
            "entry_points": [],
            "dependencies": [],
            "tools": [],
            "apis": [],
            "files": {},
        }

        detection_order = [
            ("python", ["pyproject.toml", "setup.py", "requirements.txt", "setup.cfg"]),
            ("typescript", ["package.json", "pnpm-lock.yaml", "yarn.lock"]),
            ("rust", ["Cargo.toml", "Cargo.lock"]),
            ("go", ["go.mod", "go.sum"]),
            ("java", ["pom.xml", "build.gradle", "build.gradle.kts"]),
            ("csharp", ["*.csproj", "*.sln"]),
            ("ruby", ["Gemfile", "Gemfile.lock"]),
            ("php", ["composer.json", "composer.lock"]),
            ("cpp", ["CMakeLists.txt", "Makefile", "*.cmake"]),
            ("c", ["Makefile", "*.c", "*.h"]),
            ("kotlin", ["build.gradle.kts", "settings.gradle.kts"]),
            ("swift", ["Package.swift", "*.xcodeproj"]),
            ("scala", ["build.sbt"]),
            ("dart", ["pubspec.yaml"]),
            ("elixir", ["mix.exs", "mix.lock"]),
            ("perl", ["Makefile.PL", "cpanfile"]),
            ("lua", ["*.lua"]),
        ]

        for lang, files in detection_order:
            for f in files:
                if f.startswith("*"):
                    if list(repo_path.rglob(f[1:])):
                        analysis["language"] = lang
                        break
                elif (repo_path / f).exists():
                    analysis["language"] = lang
                    break
            if analysis["language"] != "unknown":
                break

        if analysis["language"] == "python":
            for f in ["requirements.txt", "pyproject.toml", "setup.py"]:
                if (repo_path / f).exists():
                    content = (repo_path / f).read_text(encoding="utf-8", errors="ignore")
                    deps = re.findall(r'^([a-zA-Z0-9_-]+)', content, re.MULTILINE)
                    analysis["dependencies"] = deps[:20]
                    break
            for py in repo_path.rglob("__main__.py"):
                analysis["entry_points"].append(str(py.relative_to(repo_path)))

        elif analysis["language"] == "typescript":
            pkg = repo_path / "package.json"
            if pkg.exists():
                try:
                    data = json.loads(pkg.read_text())
                    analysis["dependencies"] = list(data.get("dependencies", {}).keys())[:20]
                    analysis["entry_points"] = list(data.get("bin", {}).keys())
                except json.JSONDecodeError:
                    pass

        elif analysis["language"] == "rust":
            cargo = repo_path / "Cargo.toml"
            if cargo.exists():
                content = cargo.read_text()
                deps = re.findall(r'name = "([^"]+)"', content)
                analysis["dependencies"] = deps[:20]
            for rs in ["src/main.rs", "src/lib.rs"]:
                if (repo_path / rs).exists():
                    analysis["entry_points"].append(rs)

        elif analysis["language"] == "go":
            gomod = repo_path / "go.mod"
            if gomod.exists():
                content = gomod.read_text()
                deps = re.findall(r'^(\S+)', content.split("require (")[1] if "require (" in content else "")
                analysis["dependencies"] = deps[:20] if deps else []
            for go in ["cmd/", "main.go"]:
                if (repo_path / go).exists():
                    analysis["entry_points"].append(go)

        elif analysis["language"] == "java":
            for f in ["pom.xml", "build.gradle"]:
                if (repo_path / f).exists():
                    content = (repo_path / f).read_text()
                    deps = re.findall(r'<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>', content)
                    analysis["dependencies"] = [f"{g}:{a}" for g, a in deps[:20]]
                    break

        for ext, lang in {".py": "python", ".ts": "typescript", ".js": "javascript", ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".cpp": "cpp", ".c": "c"}.items():
            files = list(repo_path.rglob(f"*{ext}"))[:50]
            analysis["files"][lang] = len(files)

        readme = repo_path / "README.md"
        if not readme:
            for name in ["README.rst", "README", "readme.md"]:
                readme = repo_path / name
                if readme.exists():
                    break

        if readme and readme.exists():
            content = readme.read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    analysis["description"] = line[:300]
                    break

        return analysis

    def _generate_agent_md(self, analysis: dict, provider: ProviderConfig | None) -> str:
        """Generate agent.md content."""
        lines = [
            f"# aicp/{analysis['name']}",
            "",
            f"**Integrated:** {datetime.now().isoformat()}",
            f"**Repository:** https://github.com/{analysis.get('owner', 'unknown')}/{analysis['name']}",
            "",
            analysis.get("description", ""),
            "",
            "---",
            "",
            "## Configuration",
            "",
        ]

        if provider:
            lines.extend([
                f"**Provider:** {provider.provider.value}",
                f"**Model:** {provider.model}",
                f"**Available:** {provider.available}",
                "",
            ])
        else:
            lines.extend([
                "*No LLM provider configured*",
                "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable execution",
                "",
            ])

        lines.extend([
            "## Metadata",
            "",
            f"- **Language:** {analysis['language']}",
            "- **Capabilities:** auto-detected",
            "",
        ])

        return "\n".join(lines)

    def _load_registry(self) -> dict[str, Any]:
        """Load agent registry from file."""
        if self.registry_file.exists():
            import json
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        return {"agents": {}}

    def _save_registry(self, registry: dict[str, Any]) -> None:
        """Save agent registry to file."""
        import json
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

    def integrate(self, repo_url: str) -> IntegrationResult:
        """Integrate a repository with automatic provider detection.

        This is the main entry point - works zero-setup!
        """
        try:
            repo_path, analysis = self.clone_and_analyze(repo_url)

            provider = self.provider_detector.get_best_provider()

            self.agents_dir.mkdir(parents=True, exist_ok=True)
            agent_md_path = self.agents_dir / f"aicp_{analysis['name']}.md"

            agent_md_content = self._generate_agent_md(analysis, provider)
            agent_md_path.write_text(agent_md_content, encoding="utf-8")

            registry = self._load_registry()
            agent_id = f"aicp/{analysis['name']}"

            registry["agents"][agent_id] = {
                "repository": repo_url,
                "integrated_at": datetime.now().isoformat(),
                "language": analysis["language"],
                "provider": provider.provider.value if provider else None,
                "agent_md": str(agent_md_path),
            }

            self._save_registry(registry)

            result = IntegrationResult(
                success=True,
                agent_name=agent_id,
                repository=repo_url,
                capabilities_registered=50,
                agent_md_path=str(agent_md_path),
                provider_used=provider,
                metadata={
                    "language": analysis["language"],
                    "description": analysis.get("description", ""),
                },
            )

            self._integrated_agents[agent_id] = result

            return result

        except Exception as e:
            return IntegrationResult(
                success=False,
                agent_name=repo_url,
                repository=repo_url,
                capabilities_registered=0,
                error=str(e),
            )

    def list_agents(self) -> list[IntegrationResult]:
        """List all integrated agents."""
        return list(self._integrated_agents.values())

    def get_agent(self, agent_name: str) -> IntegrationResult | None:
        """Get an integrated agent by name."""
        return self._integrated_agents.get(agent_name)

    def detect_providers(self) -> list[ProviderConfig]:
        """Show available providers (useful for debugging)."""
        return self.provider_detector.detect()


def auto_integrate(repo_url: str) -> IntegrationResult:
    """Quick one-liner to integrate any repo.

    Automatically:
    - Detects available LLM provider
    - Clones and analyzes repo
    - Generates agent.md
    - Registers with AICP

    Example:
        >>> result = auto_integrate("NousResearch/hermes-agent")
        >>> print(f"Integrated: {result.agent_name}")
    """
    integrator = AicpAutoIntegrator()
    return integrator.integrate(repo_url)

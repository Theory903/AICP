"""Context collector for PowerCLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class ContextCollector:
    """Collects contextual information for CLI interpretation."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def collect(self, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Collect all available context."""
        ctx = initial_context or {}

        # Git context
        ctx["git"] = self._get_git_context()

        # Project context
        ctx["project"] = self._get_project_context()

        # Working directory
        ctx["cwd"] = os.getcwd()

        # Environment
        ctx["env"] = self._get_env_context()

        # Recent commands history
        ctx["recent"] = self._get_recent_context()

        return ctx

    def _get_git_context(self) -> dict[str, Any]:
        """Get git repository context."""
        import subprocess

        ctx = {"is_repo": False}

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ctx["is_repo"] = result.returncode == 0

            if ctx["is_repo"]:
                # Get current branch
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                ctx["branch"] = result.stdout.strip() or "HEAD"

                # Get status
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                ctx["has_changes"] = bool(result.stdout.strip())

                # Get remote
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    ctx["remote"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return ctx

    def _get_project_context(self) -> dict[str, Any]:
        """Detect project type and structure."""
        ctx = {"type": "unknown", "root": Path.cwd().name}

        cwd = Path.cwd()

        # Check for common project files
        if (cwd / "pyproject.toml").exists():
            ctx["type"] = "python"
        elif (cwd / "package.json").exists():
            ctx["type"] = "node"
        elif (cwd / "Cargo.toml").exists():
            ctx["type"] = "rust"
        elif (cwd / "go.mod").exists():
            ctx["type"] = "go"

        # Check for AICP config
        aicp_dir = cwd / ".aicp"
        if aicp_dir.exists():
            ctx["aicp_configured"] = True
            if (aicp_dir / "capabilities").exists():
                ctx["capabilities_dir"] = str(aicp_dir / "capabilities")
            if (aicp_dir / "workflows").exists():
                ctx["workflows_dir"] = str(aicp_dir / "workflows")

        return ctx

    def _get_env_context(self) -> dict[str, Any]:
        """Get relevant environment variables."""
        return {
            "AICP_HOME": os.environ.get("AICP_HOME"),
            "AICP_CONFIG": os.environ.get("AICP_CONFIG"),
            "AICP_SESSION": os.environ.get("AICP_SESSION"),
        }

    def _get_recent_context(self) -> dict[str, Any]:
        """Get recent command history."""
        return {"last_command": None, "last_args": None}

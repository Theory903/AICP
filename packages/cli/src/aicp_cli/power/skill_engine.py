"""Skill engine for PowerCLI - executes registered skills/macros."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class SkillResult:
    """Result of skill execution."""

    success: bool
    command: str
    args: dict[str, Any]
    skill_name: str | None = None
    confidence: float = 1.0


class SkillEngine:
    """Executes skills/macros that map input to commands."""

    def __init__(self):
        self._skills: dict[str, dict[str, Any]] = {}
        self._load_builtin_skills()

    def _load_builtin_skills(self) -> None:
        """Load built-in skills."""
        self.register(
            name="deploy",
            pattern=r"^(deploy|release|publish)\s*(.*)",
            command="aicp run workflow.deploy",
            args={"confirm": True},
        )
        self.register(
            name="status",
            pattern=r"^(status|state|health)",
            command="aicp ls",
            args={"filter": "status"},
        )
        self.register(
            name="abort",
            pattern=r"^(abort|cancel|stop)\s*(.*)",
            command="aicp run workflow.abort",
            args={},
        )

    def register(
        self,
        name: str,
        pattern: str,
        command: str,
        args: dict[str, Any],
    ) -> None:
        """Register a skill."""
        self._skills[name] = {
            "pattern": pattern,
            "command": command,
            "args": args,
        }

    def execute(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Execute skill if input matches any skill pattern."""
        user_input = user_input.strip().lower()
        
        for skill_name, skill in self._skills.items():
            match = re.match(skill["pattern"], user_input, re.IGNORECASE)
            if match:
                # Extract captured groups
                args = dict(skill["args"])
                if match.groups():
                    args["captured"] = match.groups()
                
                return (
                    {
                        "command": skill["command"],
                        "args": args,
                        "intent": skill_name,
                        "confidence": 0.9,
                    },
                    {"skill_name": skill_name},
                )
        
        return None, {}

    def list_skills(self) -> list[str]:
        """List all registered skills."""
        return list(self._skills.keys())

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """Get skill details."""
        return self._skills.get(name)

"""Suggestion engine for PowerCLI - context-aware command suggestions."""

from __future__ import annotations

import difflib
from typing import Any


class SuggestionEngine:
    """Generates context-aware command suggestions."""

    def __init__(self, max_suggestions: int = 5):
        self.max_suggestions = max_suggestions
        self._known_commands = [
            "run",
            "dev",
            "serve",
            "scan",
            "preview",
            "ls",
            "list",
            "appr",
            "approve",
            "reject",
            "test",
            "bootstrap",
            "import",
            "init",
            "doctor",
            "history",
            "call",
            "discover",
            "map-openapi",
            "map-postman",
            "map-curl",
            "map-har",
            "policy",
            "session",
            "workflow",
            "capability",
        ]

    def suggest(
        self,
        current_input: str,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Generate suggestions based on input and context."""
        suggestions = []
        current_input = current_input.strip().lower()

        if not current_input:
            # No input - suggest common commands
            suggestions = self._get_common_suggestions(context)
        elif " " in current_input:
            # Has space - suggest arguments for the command
            cmd = current_input.split()[0]
            suggestions = self._get_arg_suggestions(cmd, current_input)
        else:
            # Partial command - autocomplete
            suggestions = self._get_command_suggestions(current_input)

        return suggestions[: self.max_suggestions]

    def _get_common_suggestions(self, context: dict[str, Any] | None) -> list[str]:
        """Get common command suggestions."""
        suggestions = ["aicp ls", "aicp dev", "aicp run"]

        if context and context.get("git", {}).get("is_repo"):
            suggestions.extend(["aicp run workflow.deploy", "aicp scan --query"])

        return suggestions

    def _get_command_suggestions(self, partial: str) -> list[str]:
        """Get command autocomplete suggestions."""
        matches = difflib.get_close_matches(
            partial,
            self._known_commands,
            n=self.max_suggestions,
            cutoff=0.6,
        )
        return [f"aicp {cmd}" for cmd in matches]

    def _get_arg_suggestions(self, cmd: str, full_input: str) -> list[str]:
        """Get argument suggestions for a command."""
        suggestions = []

        if cmd == "run":
            suggestions = [
                "aicp run --help",
                "aicp run capability.list",
                "aicp run workflow.execute",
            ]
        elif cmd == "ls" or cmd == "list":
            suggestions = [
                "aicp ls --capabilities",
                "aicp ls --workflows",
                "aicp ls --sessions",
            ]
        elif cmd == "appr" or cmd == "approve":
            suggestions = [
                "aicp appr --list",
                "aicp appr --pending",
                "aicp appr --history",
            ]

        return suggestions

    def add_command(self, command: str) -> None:
        """Add a command to the known commands list."""
        if command not in self._known_commands:
            self._known_commands.append(command)

"""Command alias resolution system."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AliasResult:
    """Result of alias resolution."""

    original: str
    expanded: str
    aliases_used: list[str]


class AliasResolver:
    """Resolves command aliases to full commands."""

    def __init__(self):
        self._aliases: dict[str, str] = {}
        self._load_default_aliases()

    def _load_default_aliases(self) -> None:
        """Load default CLI aliases."""
        # Git-style aliases
        self.register("gc", "git commit")
        self.register("gp", "git push")
        self.register("gl", "git log")
        self.register("gs", "git status")
        self.register("gd", "git diff")
        self.register("ga", "git add")
        self.register("gb", "git branch")
        self.register("gco", "git checkout")
        self.register("gm", "git merge")
        self.register("gr", "git rebase")

        # AICP command aliases
        self.register("r", "run")
        self.register("d", "dev")
        self.register("s", "scan")
        self.register("p", "preview")
        self.register("ls", "list")
        self.register("ll", "list --verbose")
        self.register("a", "appr")
        self.register("ok", "appr ok")
        self.register("no", "appr no")
        self.register("t", "test")
        self.register("b", "bootstrap")
        self.register("i", "init")
        self.register("dr", "doctor")
        self.register("h", "history")

        # Short forms
        self.register("?", "--help")
        self.register("!!", "test --all")

    def resolve(self, input_str: str) -> tuple[str, list[str]]:
        """Resolve aliases in input string."""
        original = input_str
        aliases_used = []

        # Sort aliases by length (longest first) to match most specific
        sorted_aliases = sorted(
            self._aliases.items(), key=lambda x: len(x[0]), reverse=True
        )

        for alias, expansion in sorted_aliases:
            # Match alias at start of command or after |
            pattern = rf"^\|?({re.escape(alias)})\b"
            if re.search(pattern, input_str):
                input_str = re.sub(pattern, f"\1 → {expansion}", input_str)
                aliases_used.append(alias)

        # Simple expansion if direct match
        if input_str in self._aliases:
            expansion = self._aliases[input_str]
            return expansion, [input_str]

        # Check for alias at start
        words = input_str.split()
        if words and words[0] in self._aliases:
            expansion = self._aliases[words[0]]
            words[0] = expansion
            return " ".join(words), [words[0]]

        return original, aliases_used

    def register(self, alias: str, expansion: str) -> None:
        """Register a new alias."""
        self._aliases[alias.lower()] = expansion.lower()

    def unregister(self, alias: str) -> None:
        """Unregister an alias."""
        self._aliases.pop(alias.lower(), None)

    def list_aliases(self) -> dict[str, str]:
        """List all registered aliases."""
        return self._aliases.copy()

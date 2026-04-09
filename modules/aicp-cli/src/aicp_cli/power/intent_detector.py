"""Intent detection with fuzzy matching."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class IntentResult:
    """Result of intent detection."""

    intent: str | None
    confidence: float
    transformation: str | None = None
    matched_pattern: str | None = None


class IntentDetector:
    """Detects user intent from natural language input."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self._patterns: list[dict[str, str]] = []
        self._built_in_intents = self._load_builtin_intents()

    def _load_builtin_intents(self) -> dict[str, list[dict]]:
        """Load built-in intent patterns."""
        return {
            "run": [
                {
                    "pattern": r"^(run|execute|go|start)\s+(.+)",
                    "transform": r"aicp run \2",
                },
                {"pattern": r"^(do|make|create)\s+(.+)", "transform": r"aicp run \2"},
                {"pattern": r"^!(\S+)", "transform": r"aicp run \1"},
            ],
            "approve": [
                {
                    "pattern": r"^(ok|yes|yep|approve|grant|allow)",
                    "transform": "aicp appr ok",
                },
                {"pattern": r"^y(es)?$", "transform": "aicp appr ok"},
            ],
            "reject": [
                {
                    "pattern": r"^(no|nope|deny|reject|disallow)",
                    "transform": "aicp appr no",
                },
                {"pattern": r"^n(o)?$", "transform": "aicp appr no"},
            ],
            "list": [
                {
                    "pattern": r"^(ls|list|show|what|what's available)",
                    "transform": "aicp ls",
                },
                {
                    "pattern": r"^(what can|what do|capabilities)",
                    "transform": "aicp ls",
                },
            ],
            "search": [
                {
                    "pattern": r"^(search|find|look|grep)\s+(.+)",
                    "transform": r"aicp scan --query \2",
                },
                {"pattern": r"^\?(.+)", "transform": r"aicp scan --query \1"},
            ],
            "preview": [
                {
                    "pattern": r"^(preview|inspect|show|view)\s+(.+)",
                    "transform": r"aicp preview \2",
                },
                {"pattern": r"^::(.+)", "transform": r"aicp preview \1"},
            ],
            "dev": [
                {"pattern": r"^(dev|serve|start|run server)", "transform": "aicp dev"},
                {"pattern": r"^d$", "transform": "aicp dev"},
            ],
            "test": [
                {"pattern": r"^(test|check|validate|verify)", "transform": "aicp test"},
                {"pattern": r"^t$", "transform": "aicp test"},
            ],
            "help": [
                {"pattern": r"^(help|\?|man)", "transform": "aicp --help"},
                {"pattern": r"^(what is|how|explain)", "transform": "aicp --help"},
            ],
        }

    def detect(
        self, input_str: str, context: dict[str, Any] | None = None
    ) -> IntentResult:
        """Detect intent from user input."""
        input_str = input_str.strip().lower()

        # Try built-in patterns first
        for intent_name, patterns in self._built_in_intents.items():
            for pattern in patterns:
                match = re.match(pattern["pattern"], input_str, re.IGNORECASE)
                if match:
                    transformation = re.sub(
                        pattern["pattern"],
                        pattern["transform"],
                        input_str,
                        flags=re.IGNORECASE,
                    )
                    return IntentResult(
                        intent=intent_name,
                        confidence=0.95,
                        transformation=transformation,
                        matched_pattern=pattern["pattern"],
                    )

        # Try registered patterns
        for pattern_def in self._patterns:
            match = re.match(pattern_def["pattern"], input_str, re.IGNORECASE)
            if match:
                transformation = re.sub(
                    pattern_def["pattern"],
                    pattern_def["transformation"],
                    input_str,
                    flags=re.IGNORECASE,
                )
                return IntentResult(
                    intent=pattern_def.get("intent"),
                    confidence=0.85,
                    transformation=transformation,
                    matched_pattern=pattern_def["pattern"],
                )

        # Fuzzy match against known commands
        known_commands = [
            "run",
            "dev",
            "scan",
            "preview",
            "ls",
            "list",
            "appr",
            "approve",
            "test",
            "bootstrap",
            "import",
            "init",
            "doctor",
            "serve",
            "history",
            "protect",
        ]

        best_match = None
        best_ratio = 0.0

        for cmd in known_commands:
            ratio = difflib.SequenceMatcher(None, input_str, cmd).ratio()
            if ratio > best_ratio and ratio >= self.threshold:
                best_match = cmd
                best_ratio = ratio

        if best_match:
            # Check if input might be the command itself
            if input_str == best_match:
                return IntentResult(
                    intent="direct",
                    confidence=1.0,
                    transformation=f"aicp {best_match}",
                )
            # Input contains the command
            if best_match in input_str:
                return IntentResult(
                    intent="partial",
                    confidence=best_ratio,
                    transformation=f"aicp {input_str}",
                )

        # No intent detected - return as-is
        return IntentResult(
            intent=None,
            confidence=1.0,
            transformation=f"aicp {input_str}" if input_str else None,
        )

    def register_pattern(
        self,
        pattern: str,
        intent: str,
        transformation: str,
    ) -> None:
        """Register a custom intent pattern."""
        self._patterns.append(
            {
                "pattern": pattern,
                "intent": intent,
                "transformation": transformation,
            }
        )

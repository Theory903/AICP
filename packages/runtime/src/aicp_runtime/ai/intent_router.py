"""Intent Router for AICP.

Maps a natural language utterance to one of four routing destinations:
  - CAPABILITY  → execute a single known capability immediately
  - PLAN        → generate a multi-step plan (hand off to AICPlanner)
  - CLARIFY     → ask a clarifying question before routing further
  - REJECT      → the intent cannot or should not be fulfilled

Design:
  - Token overlap scoring (same heuristic as AICPlanner) for capability match.
  - Multi-step indicators checked before capability matching.
  - Prohibited keywords checked first (fail-closed).
  - If best capability score < clarify_threshold → CLARIFY.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class IntentRouterError(Exception):
    """Base exception for Intent Router errors."""


# ---------------------------------------------------------------------------
# RoutingDestination enum
# ---------------------------------------------------------------------------


class RoutingDestination(str, Enum):
    CAPABILITY = "capability"
    PLAN = "plan"
    CLARIFY = "clarify"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# RouteDecision
# ---------------------------------------------------------------------------


@dataclass
class RouteDecision:
    """Result of routing an utterance."""

    destination: RoutingDestination
    confidence: float = 0.0
    capability_name: Optional[str] = None
    clarification_prompt: Optional[str] = None
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------

_DEFAULT_MULTI_STEP_INDICATORS: list[str] = [
    "and then",
    "followed by",
    "after",
    "sequence",
    "also",
    "first",  # used with "then" pattern below — checked by regex
    "then",
]

_DEFAULT_PROHIBITED_KEYWORDS: list[str] = [
    "delete all",
    "drop database",
    "format disk",
]

# Regex for "first … then" pattern (case-insensitive)
_FIRST_THEN_RE = re.compile(r"\bfirst\b.*\bthen\b", re.IGNORECASE)

_CLARIFY_THRESHOLD_DEFAULT = 0.15


# ---------------------------------------------------------------------------
# IntentRouter
# ---------------------------------------------------------------------------


def _tokenise(text: str) -> set[str]:
    """Lowercase, split on non-word chars, discard stop words."""
    _STOP = {
        "a", "an", "the", "to", "of", "for", "is", "are", "in", "on",
        "my", "me", "i", "it", "at", "by", "with", "from", "this", "that",
        "and", "or", "not", "be", "do", "please",
    }
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if t not in _STOP}


def _score(utterance_tokens: set[str], capability: dict[str, Any]) -> float:
    """Token-overlap score between utterance and a capability dict."""
    cap_text = f"{capability.get('name', '')} {capability.get('description', '')}"
    cap_tokens = _tokenise(cap_text)
    if not cap_tokens:
        return 0.0
    overlap = utterance_tokens & cap_tokens
    return len(overlap) / len(cap_tokens)


class IntentRouter:
    """Routes natural language utterances to AICP execution destinations."""

    def __init__(
        self,
        capabilities: list[dict[str, Any]],
        clarify_threshold: float = _CLARIFY_THRESHOLD_DEFAULT,
        multi_step_indicators: Optional[list[str]] = None,
        prohibited_keywords: Optional[list[str]] = None,
    ) -> None:
        if capabilities is None:
            raise IntentRouterError("capabilities must be a list, not None")

        self._capabilities = capabilities
        self._clarify_threshold = clarify_threshold
        self._custom_indicators = multi_step_indicators is not None
        self._multi_step_indicators: list[str] = (
            multi_step_indicators
            if multi_step_indicators is not None
            else list(_DEFAULT_MULTI_STEP_INDICATORS)
        )
        self._prohibited_keywords: list[str] = (
            prohibited_keywords
            if prohibited_keywords is not None
            else list(_DEFAULT_PROHIBITED_KEYWORDS)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, utterance: str) -> RouteDecision:
        """Route *utterance* and return a RouteDecision."""
        text = utterance.strip()

        # 1. Reject prohibited operations first (fail-closed).
        for kw in self._prohibited_keywords:
            if kw.lower() in text.lower():
                return RouteDecision(
                    destination=RoutingDestination.REJECT,
                    confidence=1.0,
                    rejection_reason=f"Prohibited operation detected: '{kw}'",
                )

        # 2. Empty or no-op utterance → CLARIFY immediately.
        if not text:
            return RouteDecision(
                destination=RoutingDestination.CLARIFY,
                confidence=1.0,
                clarification_prompt="What would you like to do?",
            )

        # 3. No capabilities registered → cannot route → CLARIFY.
        if not self._capabilities:
            return RouteDecision(
                destination=RoutingDestination.CLARIFY,
                confidence=1.0,
                clarification_prompt=(
                    "No capabilities are available. Please describe your goal."
                ),
            )

        # 4. Multi-step detection → PLAN.
        if self._is_multi_step(text):
            return RouteDecision(
                destination=RoutingDestination.PLAN,
                confidence=0.8,
            )

        # 5. Score all capabilities; pick best.
        tokens = _tokenise(text)
        scored = sorted(
            [(cap, _score(tokens, cap)) for cap in self._capabilities],
            key=lambda x: x[1],
            reverse=True,
        )
        best_cap, best_score = scored[0]

        # 6. Below threshold → CLARIFY.
        if best_score < self._clarify_threshold:
            return RouteDecision(
                destination=RoutingDestination.CLARIFY,
                confidence=1.0 - best_score,
                clarification_prompt=(
                    "I'm not sure what you'd like to do. "
                    "Could you be more specific?"
                ),
            )

        # 7. Route to the best matching capability.
        return RouteDecision(
            destination=RoutingDestination.CAPABILITY,
            capability_name=best_cap["name"],
            confidence=min(best_score, 1.0),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_multi_step(self, text: str) -> bool:
        """Return True if *text* contains multi-step indicators."""
        lower = text.lower()

        # "first … then" pattern (requires both words)
        if _FIRST_THEN_RE.search(text):
            return True

        # Multi-word indicators (e.g. "and then", "followed by")
        for indicator in self._multi_step_indicators:
            ind_lower = indicator.lower()
            # Skip single-word indicators that are also common stop words
            # unless they appear as the primary signal (handled by regex above).
            if " " in ind_lower:
                if ind_lower in lower:
                    return True
            else:
                # Single-word: use word-boundary match.
                if re.search(r"\b" + re.escape(ind_lower) + r"\b", lower):
                    # When using default indicators, skip "first"/"then" as
                    # they are handled more precisely by _FIRST_THEN_RE above.
                    if not self._custom_indicators and ind_lower in {"first", "then"}:
                        continue
                    return True

        return False

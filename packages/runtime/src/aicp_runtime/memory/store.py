"""5-layer Memory System for AICP sessions.

Layers (per session.schema.json):
  1. WorkingMemory   — in-flight data for the current task (cleared on session end)
  2. EpisodicMemory  — ordered log of key events / decisions
  3. SemanticMemory  — persistent facts and entities
  4. ProceduralMemory — learned workflow patterns and skill sequences
  5. MetaMemory      — self-model: token budget, coverage, preference weights
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# WorkingMemory
# ---------------------------------------------------------------------------


class WorkingMemory:
    """In-flight key-value store for the current task.  Cleared on session end."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkingMemory":
        wm = cls()
        wm._data = dict(data)
        return wm


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------


@dataclass
class EpisodicEvent:
    event: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"event": self.event, "timestamp": self.timestamp, "data": self.data}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EpisodicEvent":
        return cls(
            event=d["event"],
            timestamp=d["timestamp"],
            data=d.get("data", {}),
        )


class EpisodicMemory:
    """Ordered log of key events, decisions, and observations in this session."""

    def __init__(self) -> None:
        self._events: list[EpisodicEvent] = []

    def append(self, event: str, data: Optional[dict[str, Any]] = None) -> None:
        self._events.append(
            EpisodicEvent(
                event=event,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data=data or {},
            )
        )

    def all(self) -> list[EpisodicEvent]:
        return list(self._events)

    def to_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events]

    @classmethod
    def from_list(cls, items: list[dict[str, Any]]) -> "EpisodicMemory":
        em = cls()
        em._events = [EpisodicEvent.from_dict(item) for item in items]
        return em


# ---------------------------------------------------------------------------
# SemanticMemory
# ---------------------------------------------------------------------------


class SemanticMemory:
    """Persistent facts and entities known about the domain."""

    def __init__(self) -> None:
        self._facts: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._facts[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._facts.get(key, default)

    def keys(self) -> list[str]:
        return list(self._facts.keys())

    def to_dict(self) -> dict[str, Any]:
        return dict(self._facts)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticMemory":
        sm = cls()
        sm._facts = dict(data)
        return sm


# ---------------------------------------------------------------------------
# ProceduralMemory
# ---------------------------------------------------------------------------


@dataclass
class ProceduralPattern:
    pattern: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {"pattern": self.pattern, "confidence": self.confidence}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProceduralPattern":
        return cls(pattern=d["pattern"], confidence=d.get("confidence", 0.0))


class ProceduralMemory:
    """Learned workflow patterns and skill sequences."""

    def __init__(self) -> None:
        self._patterns: list[ProceduralPattern] = []

    def add_pattern(self, pattern: str, confidence: float = 1.0) -> None:
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {confidence}"
            )
        self._patterns.append(ProceduralPattern(pattern=pattern, confidence=confidence))

    def all(self) -> list[ProceduralPattern]:
        return list(self._patterns)

    def best(self) -> Optional[ProceduralPattern]:
        if not self._patterns:
            return None
        return max(self._patterns, key=lambda p: p.confidence)

    def to_list(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._patterns]

    @classmethod
    def from_list(cls, items: list[dict[str, Any]]) -> "ProceduralMemory":
        pm = cls()
        pm._patterns = [ProceduralPattern.from_dict(item) for item in items]
        return pm


# ---------------------------------------------------------------------------
# MetaMemory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TokenBudgetExhaustedError
# ---------------------------------------------------------------------------


class TokenBudgetExhaustedError(Exception):
    """Raised when a consume_tokens call would exceed the remaining budget."""


# ---------------------------------------------------------------------------
# MetaMemory (continued)
# ---------------------------------------------------------------------------


class MetaMemory:
    """Self-model: token budget, capability coverage, preference weights."""

    def __init__(
        self,
        token_budget_remaining: int = 0,
        capability_coverage: Optional[list[str]] = None,
        preference_weights: Optional[dict[str, float]] = None,
    ) -> None:
        self.token_budget_remaining: int = token_budget_remaining
        self.capability_coverage: list[str] = list(capability_coverage or [])
        self.preference_weights: dict[str, float] = dict(preference_weights or {})

    # ------------------------------------------------------------------
    # Token budget API
    # ------------------------------------------------------------------

    def has_budget(self) -> bool:
        """Return True if there are tokens remaining in the budget."""
        return self.token_budget_remaining > 0

    def consume_tokens(self, tokens: int) -> None:
        """Deduct *tokens* from the remaining budget.

        Raises:
            ValueError: if *tokens* is negative.
            TokenBudgetExhaustedError: if the deduction would make the budget
                go below zero (budget remains unchanged on failure).
        """
        if tokens < 0:
            raise ValueError(
                f"tokens to consume must be non-negative, got: {tokens}"
            )
        if tokens > self.token_budget_remaining:
            raise TokenBudgetExhaustedError(
                f"Token budget exhausted: requested {tokens}, "
                f"remaining {self.token_budget_remaining}"
            )
        self.token_budget_remaining -= tokens

    def set_token_budget(self, budget: int) -> None:
        """Replace the current budget with a new value.

        Raises:
            ValueError: if *budget* is negative.
        """
        if budget < 0:
            raise ValueError(f"budget must be non-negative, got: {budget}")
        self.token_budget_remaining = budget

    # ------------------------------------------------------------------
    # Coverage / preferences
    # ------------------------------------------------------------------

    def add_coverage(self, pattern: str) -> None:
        if pattern not in self.capability_coverage:
            self.capability_coverage.append(pattern)

    def set_preference(self, key: str, weight: float) -> None:
        self.preference_weights[key] = weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_budget_remaining": self.token_budget_remaining,
            "capability_coverage": list(self.capability_coverage),
            "preference_weights": dict(self.preference_weights),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetaMemory":
        return cls(
            token_budget_remaining=data.get("token_budget_remaining", 0),
            capability_coverage=list(data.get("capability_coverage", [])),
            preference_weights=dict(data.get("preference_weights", {})),
        )


# ---------------------------------------------------------------------------
# MemorySnapshot
# ---------------------------------------------------------------------------


@dataclass
class MemorySnapshot:
    """Serialisable point-in-time snapshot of all 5 memory layers."""

    working: dict[str, Any] = field(default_factory=dict)
    episodic: list[dict[str, Any]] = field(default_factory=list)
    semantic: dict[str, Any] = field(default_factory=dict)
    procedural: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "working": self.working,
            "episodic": self.episodic,
            "semantic": self.semantic,
            "procedural": self.procedural,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemorySnapshot":
        return cls(
            working=data.get("working", {}),
            episodic=data.get("episodic", []),
            semantic=data.get("semantic", {}),
            procedural=data.get("procedural", []),
            meta=data.get("meta", {}),
        )


# ---------------------------------------------------------------------------
# MemoryStore  (5-layer aggregator)
# ---------------------------------------------------------------------------


class MemoryStore:
    """Aggregates all 5 memory layers into a single session-scoped object."""

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.meta = MetaMemory()

    def snapshot(self) -> MemorySnapshot:
        """Return a serialisable snapshot of all 5 layers."""
        return MemorySnapshot(
            working=self.working.to_dict(),
            episodic=self.episodic.to_list(),
            semantic=self.semantic.to_dict(),
            procedural=self.procedural.to_list(),
            meta=self.meta.to_dict(),
        )

    @classmethod
    def from_snapshot(cls, snap: MemorySnapshot) -> "MemoryStore":
        """Restore a MemoryStore from a previously taken snapshot."""
        store = cls()
        store.working = WorkingMemory.from_dict(snap.working)
        store.episodic = EpisodicMemory.from_list(snap.episodic)
        store.semantic = SemanticMemory.from_dict(snap.semantic)
        store.procedural = ProceduralMemory.from_list(snap.procedural)
        store.meta = MetaMemory.from_dict(snap.meta)
        return store

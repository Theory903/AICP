"""Research Cognitive Protocol for AICP.

Governs how the agent performs information gathering and knowledge synthesis.
Every research action the agent initiates goes through this protocol so that:
  - Research actions are structured and auditable.
  - Required fields are enforced per operation type.
  - Confidence scores are validated.
  - The agent tracks research actions per session.

Operations:
  SEARCH    — search for information using a query string
  FETCH     — retrieve content from a URL
  SUMMARIZE — summarize a source text (supports optional confidence score)
  COMPARE   — compare two or more items
  EXTRACT   — extract structured data from a source (requires schema)
  CITE      — generate a citation for a URL
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class ResearchProtocolError(Exception):
    """Raised when a Research protocol constraint is violated."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ResearchOperationType(str, Enum):
    SEARCH = "search"
    FETCH = "fetch"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    EXTRACT = "extract"
    CITE = "cite"


# ---------------------------------------------------------------------------
# ResearchAction
# ---------------------------------------------------------------------------


@dataclass
class ResearchAction:
    """A structured research/information-gathering operation."""

    operation: ResearchOperationType
    query: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    items: Optional[list[str]] = None
    extract_schema: Optional[dict[str, Any]] = None
    citation_style: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "query": self.query,
            "url": self.url,
            "source": self.source,
            "items": self.items,
            "extract_schema": self.extract_schema,
            "citation_style": self.citation_style,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# ResearchProtocol
# ---------------------------------------------------------------------------


class ResearchProtocol:
    """Manages structured research actions for a session."""

    def __init__(self) -> None:
        self._history: list[ResearchAction] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[ResearchAction]:
        return list(self._history)

    @property
    def search_count(self) -> int:
        return sum(
            1 for a in self._history if a.operation == ResearchOperationType.SEARCH
        )

    # ------------------------------------------------------------------
    # Action builders
    # ------------------------------------------------------------------

    def search(self, query: str) -> ResearchAction:
        """Create a SEARCH action."""
        if not query or not query.strip():
            raise ResearchProtocolError("query must not be empty")
        action = ResearchAction(
            operation=ResearchOperationType.SEARCH,
            query=query,
        )
        self._record(action)
        return action

    def fetch(self, url: str) -> ResearchAction:
        """Create a FETCH action (requires non-empty URL)."""
        if not url or not url.strip():
            raise ResearchProtocolError("url must not be empty")
        action = ResearchAction(
            operation=ResearchOperationType.FETCH,
            url=url,
        )
        self._record(action)
        return action

    def summarize(
        self, source: str, confidence: Optional[float] = None
    ) -> ResearchAction:
        """Create a SUMMARIZE action with optional confidence score [0, 1]."""
        if not source or not source.strip():
            raise ResearchProtocolError("source must not be empty")
        if confidence is not None:
            self._validate_confidence(confidence)
        action = ResearchAction(
            operation=ResearchOperationType.SUMMARIZE,
            source=source,
            confidence=confidence,
        )
        self._record(action)
        return action

    def compare(self, items: list[str]) -> ResearchAction:
        """Create a COMPARE action (requires at least two items)."""
        if not items or len(items) < 2:
            raise ResearchProtocolError(
                "items must contain at least two entries for COMPARE"
            )
        action = ResearchAction(
            operation=ResearchOperationType.COMPARE,
            items=list(items),
        )
        self._record(action)
        return action

    def extract(
        self, source: str, schema: Optional[dict[str, Any]]
    ) -> ResearchAction:
        """Create an EXTRACT action (requires non-empty source and schema)."""
        if not source or not source.strip():
            raise ResearchProtocolError("source must not be empty")
        if schema is None:
            raise ResearchProtocolError("schema is required for EXTRACT operations")
        action = ResearchAction(
            operation=ResearchOperationType.EXTRACT,
            source=source,
            extract_schema=dict(schema),
        )
        self._record(action)
        return action

    def cite(self, url: str, style: str = "APA") -> ResearchAction:
        """Create a CITE action (requires non-empty URL)."""
        if not url or not url.strip():
            raise ResearchProtocolError("url must not be empty")
        action = ResearchAction(
            operation=ResearchOperationType.CITE,
            url=url,
            citation_style=style,
        )
        self._record(action)
        return action

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_confidence(self, confidence: float) -> None:
        if not (0.0 <= confidence <= 1.0):
            raise ResearchProtocolError(
                f"confidence must be between 0.0 and 1.0, got: {confidence}"
            )

    def _record(self, action: ResearchAction) -> None:
        self._history.append(action)

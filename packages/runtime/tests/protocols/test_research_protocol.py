"""Tests for the Research Cognitive Protocol (TDD).

The Research Protocol governs how the agent performs information gathering
and knowledge synthesis:
  - Produces a ResearchAction (a structured research operation)
  - Classifies operation type: SEARCH, FETCH, SUMMARIZE, COMPARE,
    EXTRACT, CITE
  - Enforces required fields per operation type
  - Validates query/url/source (non-empty)
  - Tracks research actions per session
  - Supports confidence scoring for SUMMARIZE and EXTRACT results
"""

from __future__ import annotations

import pytest

from aicp_runtime.protocols.research import (
    ResearchProtocol,
    ResearchAction,
    ResearchOperationType,
    ResearchProtocolError,
)


# ---------------------------------------------------------------------------
# ResearchAction
# ---------------------------------------------------------------------------


class TestResearchAction:
    def test_search_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.SEARCH,
            query="AICP protocol specification",
        )
        assert action.operation == ResearchOperationType.SEARCH
        assert action.query == "AICP protocol specification"

    def test_fetch_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.FETCH,
            url="https://example.com/docs",
        )
        assert action.url == "https://example.com/docs"

    def test_summarize_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.SUMMARIZE,
            source="long document text here",
        )
        assert action.source == "long document text here"

    def test_compare_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.COMPARE,
            items=["option A", "option B", "option C"],
        )
        assert action.items == ["option A", "option B", "option C"]

    def test_extract_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.EXTRACT,
            source="document text",
            extract_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        assert action.extract_schema is not None

    def test_cite_action_fields(self):
        action = ResearchAction(
            operation=ResearchOperationType.CITE,
            url="https://example.com/paper",
            citation_style="APA",
        )
        assert action.citation_style == "APA"

    def test_confidence_defaults_to_none(self):
        action = ResearchAction(
            operation=ResearchOperationType.SEARCH,
            query="test",
        )
        assert action.confidence is None

    def test_confidence_can_be_set(self):
        action = ResearchAction(
            operation=ResearchOperationType.SUMMARIZE,
            source="text",
            confidence=0.87,
        )
        assert action.confidence == pytest.approx(0.87)

    def test_to_dict_includes_operation(self):
        action = ResearchAction(
            operation=ResearchOperationType.SEARCH,
            query="test query",
        )
        d = action.to_dict()
        assert d["operation"] == "search"
        assert d["query"] == "test query"


# ---------------------------------------------------------------------------
# ResearchProtocol
# ---------------------------------------------------------------------------


class TestResearchProtocol:
    # ------------------------------------------------------------------
    # Action builders — happy path
    # ------------------------------------------------------------------

    def test_search_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.search("AICP protocol")
        assert isinstance(action, ResearchAction)
        assert action.operation == ResearchOperationType.SEARCH

    def test_fetch_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.fetch("https://example.com/doc")
        assert action.operation == ResearchOperationType.FETCH
        assert action.url == "https://example.com/doc"

    def test_summarize_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.summarize("A long text about AICP...")
        assert action.operation == ResearchOperationType.SUMMARIZE
        assert action.source == "A long text about AICP..."

    def test_compare_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.compare(["option A", "option B"])
        assert action.operation == ResearchOperationType.COMPARE
        assert action.items == ["option A", "option B"]

    def test_extract_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.extract(
            "text with data",
            schema={"type": "object"},
        )
        assert action.operation == ResearchOperationType.EXTRACT
        assert action.extract_schema == {"type": "object"}

    def test_cite_returns_research_action(self):
        rp = ResearchProtocol()
        action = rp.cite("https://example.com/paper", style="APA")
        assert action.operation == ResearchOperationType.CITE
        assert action.citation_style == "APA"

    # ------------------------------------------------------------------
    # Validation — required fields
    # ------------------------------------------------------------------

    def test_search_requires_non_empty_query(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="query"):
            rp.search("")

    def test_search_rejects_whitespace_query(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="query"):
            rp.search("   ")

    def test_fetch_requires_url(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="url"):
            rp.fetch("")

    def test_summarize_requires_source(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="source"):
            rp.summarize("")

    def test_compare_requires_at_least_two_items(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="items"):
            rp.compare(["only one"])

    def test_compare_rejects_empty_list(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="items"):
            rp.compare([])

    def test_extract_requires_source(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="source"):
            rp.extract("", schema={"type": "object"})

    def test_extract_requires_schema(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="schema"):
            rp.extract("some text", schema=None)  # type: ignore[arg-type]

    def test_cite_requires_url(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="url"):
            rp.cite("", style="APA")

    # ------------------------------------------------------------------
    # Confidence validation
    # ------------------------------------------------------------------

    def test_confidence_must_be_between_0_and_1(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="confidence"):
            rp.summarize("text", confidence=1.5)

    def test_confidence_cannot_be_negative(self):
        rp = ResearchProtocol()
        with pytest.raises(ResearchProtocolError, match="confidence"):
            rp.summarize("text", confidence=-0.1)

    def test_confidence_boundary_values_accepted(self):
        rp = ResearchProtocol()
        a0 = rp.summarize("text 1", confidence=0.0)
        a1 = rp.summarize("text 2", confidence=1.0)
        assert a0.confidence == pytest.approx(0.0)
        assert a1.confidence == pytest.approx(1.0)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def test_history_tracks_all_actions(self):
        rp = ResearchProtocol()
        rp.search("query 1")
        rp.fetch("https://example.com")
        rp.summarize("some text")
        assert len(rp.history) == 3

    def test_history_is_ordered(self):
        rp = ResearchProtocol()
        rp.search("first")
        rp.fetch("https://example.com")
        assert rp.history[0].operation == ResearchOperationType.SEARCH
        assert rp.history[1].operation == ResearchOperationType.FETCH

    def test_clear_history(self):
        rp = ResearchProtocol()
        rp.search("test")
        rp.clear_history()
        assert rp.history == []

    def test_history_is_a_copy(self):
        rp = ResearchProtocol()
        rp.search("test")
        h = rp.history
        h.clear()
        assert len(rp.history) == 1

    def test_search_count(self):
        rp = ResearchProtocol()
        rp.search("q1")
        rp.search("q2")
        rp.fetch("https://example.com")
        assert rp.search_count == 2

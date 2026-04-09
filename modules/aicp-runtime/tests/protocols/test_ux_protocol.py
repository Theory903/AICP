"""Tests for the UX Cognitive Protocol (TDD).

The UX Protocol governs agent-human interaction surfaces:
  - Produces a PromptBlock (a structured question/choice/confirmation to show the user)
  - Classifies interaction type: QUESTION, CHOICE, CONFIRMATION, NOTIFICATION
  - Enforces max-options limit for CHOICE blocks
  - Tracks conversation turns per session
  - Renders to a plain-text string
"""

from __future__ import annotations

import pytest

from aicp_runtime.protocols.ux import (
    UXProtocol,
    PromptBlock,
    InteractionType,
    UXProtocolError,
)


# ---------------------------------------------------------------------------
# PromptBlock
# ---------------------------------------------------------------------------


class TestPromptBlock:
    def test_question_block_fields(self):
        pb = PromptBlock(
            interaction_type=InteractionType.QUESTION,
            message="What item would you like to add?",
        )
        assert pb.interaction_type == InteractionType.QUESTION
        assert pb.message == "What item would you like to add?"
        assert pb.options is None
        assert pb.default is None

    def test_choice_block_requires_options(self):
        pb = PromptBlock(
            interaction_type=InteractionType.CHOICE,
            message="Select a payment method",
            options=["credit card", "debit card", "PayPal"],
        )
        assert len(pb.options) == 3

    def test_confirmation_block(self):
        pb = PromptBlock(
            interaction_type=InteractionType.CONFIRMATION,
            message="Are you sure you want to place the order?",
            default="yes",
        )
        assert pb.default == "yes"

    def test_notification_block(self):
        pb = PromptBlock(
            interaction_type=InteractionType.NOTIFICATION,
            message="Order placed successfully.",
        )
        assert pb.interaction_type == InteractionType.NOTIFICATION

    def test_render_question(self):
        pb = PromptBlock(
            interaction_type=InteractionType.QUESTION,
            message="What is your dietary restriction?",
        )
        rendered = pb.render()
        assert "What is your dietary restriction?" in rendered

    def test_render_choice_includes_options(self):
        pb = PromptBlock(
            interaction_type=InteractionType.CHOICE,
            message="Pick one:",
            options=["A", "B", "C"],
        )
        rendered = pb.render()
        assert "A" in rendered
        assert "B" in rendered
        assert "C" in rendered

    def test_render_confirmation_includes_default(self):
        pb = PromptBlock(
            interaction_type=InteractionType.CONFIRMATION,
            message="Confirm order?",
            default="yes",
        )
        rendered = pb.render()
        assert "yes" in rendered.lower() or "confirm" in rendered.lower()

    def test_to_dict_roundtrip(self):
        pb = PromptBlock(
            interaction_type=InteractionType.CHOICE,
            message="Select option",
            options=["X", "Y"],
        )
        d = pb.to_dict()
        assert d["interaction_type"] == "choice"
        assert d["options"] == ["X", "Y"]


# ---------------------------------------------------------------------------
# UXProtocol
# ---------------------------------------------------------------------------


class TestUXProtocol:
    def test_ask_returns_question_block(self):
        ux = UXProtocol()
        block = ux.ask("What would you like to order?")
        assert isinstance(block, PromptBlock)
        assert block.interaction_type == InteractionType.QUESTION

    def test_choose_returns_choice_block(self):
        ux = UXProtocol()
        block = ux.choose("Select delivery method", options=["standard", "express"])
        assert block.interaction_type == InteractionType.CHOICE
        assert "express" in block.options

    def test_confirm_returns_confirmation_block(self):
        ux = UXProtocol()
        block = ux.confirm("Place this order?")
        assert block.interaction_type == InteractionType.CONFIRMATION

    def test_notify_returns_notification_block(self):
        ux = UXProtocol()
        block = ux.notify("Your order has been placed.")
        assert block.interaction_type == InteractionType.NOTIFICATION

    def test_choose_enforces_max_options(self):
        ux = UXProtocol(max_options=3)
        with pytest.raises(UXProtocolError, match="max_options"):
            ux.choose("Pick", options=["a", "b", "c", "d"])

    def test_choose_requires_at_least_one_option(self):
        ux = UXProtocol()
        with pytest.raises(UXProtocolError):
            ux.choose("Pick", options=[])

    def test_turn_counter_increments(self):
        ux = UXProtocol()
        assert ux.turn_count == 0
        ux.ask("q1")
        assert ux.turn_count == 1
        ux.notify("n1")
        assert ux.turn_count == 2

    def test_history_records_all_blocks(self):
        ux = UXProtocol()
        ux.ask("q1")
        ux.notify("done")
        assert len(ux.history) == 2
        assert ux.history[0].interaction_type == InteractionType.QUESTION

    def test_clear_history(self):
        ux = UXProtocol()
        ux.ask("q1")
        ux.clear_history()
        assert ux.history == []
        assert ux.turn_count == 0

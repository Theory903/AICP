"""Tests for the Intent Router (TDD — tests first).

The Intent Router maps a natural language utterance to one of four routing
destinations:
  - CAPABILITY   → execute a single known capability immediately
  - PLAN         → generate a multi-step plan (hand off to AICPlanner)
  - CLARIFY      → ask a clarifying question before routing further
  - REJECT       → the intent cannot or should not be fulfilled

Design rules (derived from AICP spec):
  - Routing is deterministic given capabilities + utterance.
  - The router returns a RouteDecision with a destination, matched capability
    name (if CAPABILITY), and a confidence score.
  - If confidence < threshold, the router escalates to CLARIFY.
  - Multi-step indicators ("and then", "after", "followed by", "also",
    "sequence", "first ... then") route to PLAN.
  - Prohibited keywords ("delete all", "drop database", "format disk") route
    to REJECT.
  - Token overlap scoring (same heuristic as the planner) is used for
    capability matching.
"""

from __future__ import annotations

import pytest

from aicp_runtime.ai.intent_router import (
    IntentRouter,
    RouteDecision,
    RoutingDestination,
    IntentRouterError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CAPABILITIES = [
    {
        "name": "cart.add_item",
        "description": "Add an item to the shopping cart",
        "kind": "action",
    },
    {
        "name": "cart.remove_item",
        "description": "Remove an item from the shopping cart",
        "kind": "action",
    },
    {
        "name": "checkout.start",
        "description": "Begin the checkout process",
        "kind": "action",
    },
    {
        "name": "payments.charge",
        "description": "Charge a payment method for the current order",
        "kind": "action",
    },
    {
        "name": "order.track",
        "description": "Track the status of an existing order",
        "kind": "query",
    },
    {
        "name": "account.update_profile",
        "description": "Update user account profile information",
        "kind": "action",
    },
]


# ---------------------------------------------------------------------------
# RouteDecision
# ---------------------------------------------------------------------------


class TestRouteDecision:
    def test_capability_decision_fields(self):
        d = RouteDecision(
            destination=RoutingDestination.CAPABILITY,
            capability_name="cart.add_item",
            confidence=0.9,
        )
        assert d.destination == RoutingDestination.CAPABILITY
        assert d.capability_name == "cart.add_item"
        assert d.confidence == 0.9

    def test_plan_decision_no_capability_name(self):
        d = RouteDecision(
            destination=RoutingDestination.PLAN,
            confidence=0.75,
        )
        assert d.destination == RoutingDestination.PLAN
        assert d.capability_name is None

    def test_clarify_decision(self):
        d = RouteDecision(
            destination=RoutingDestination.CLARIFY,
            confidence=0.3,
            clarification_prompt="What item would you like to add?",
        )
        assert d.destination == RoutingDestination.CLARIFY
        assert "item" in d.clarification_prompt

    def test_reject_decision(self):
        d = RouteDecision(
            destination=RoutingDestination.REJECT,
            confidence=1.0,
            rejection_reason="Prohibited operation requested",
        )
        assert d.destination == RoutingDestination.REJECT
        assert d.rejection_reason is not None


# ---------------------------------------------------------------------------
# IntentRouter — single-capability routing
# ---------------------------------------------------------------------------


class TestIntentRouterCapabilityRouting:
    def setup_method(self):
        self.router = IntentRouter(capabilities=SAMPLE_CAPABILITIES)

    def test_routes_to_known_capability(self):
        decision = self.router.route("add item to cart")
        assert decision.destination == RoutingDestination.CAPABILITY
        assert decision.capability_name == "cart.add_item"
        assert decision.confidence > 0.0

    def test_routes_checkout(self):
        decision = self.router.route("start checkout")
        assert decision.destination == RoutingDestination.CAPABILITY
        assert decision.capability_name == "checkout.start"

    def test_routes_track_order(self):
        decision = self.router.route("track my order status")
        assert decision.destination == RoutingDestination.CAPABILITY
        assert decision.capability_name == "order.track"

    def test_routes_payment(self):
        decision = self.router.route("charge my payment method")
        assert decision.destination == RoutingDestination.CAPABILITY
        assert decision.capability_name == "payments.charge"

    def test_confidence_is_between_0_and_1(self):
        decision = self.router.route("add item to cart")
        assert 0.0 <= decision.confidence <= 1.0


# ---------------------------------------------------------------------------
# IntentRouter — multi-step → PLAN
# ---------------------------------------------------------------------------


class TestIntentRouterPlanRouting:
    def setup_method(self):
        self.router = IntentRouter(capabilities=SAMPLE_CAPABILITIES)

    def test_and_then_routes_to_plan(self):
        decision = self.router.route("add item to cart and then checkout")
        assert decision.destination == RoutingDestination.PLAN

    def test_followed_by_routes_to_plan(self):
        decision = self.router.route("start checkout followed by charging payment")
        assert decision.destination == RoutingDestination.PLAN

    def test_sequence_keyword_routes_to_plan(self):
        decision = self.router.route("sequence: add item, checkout, pay")
        assert decision.destination == RoutingDestination.PLAN

    def test_first_then_routes_to_plan(self):
        decision = self.router.route("first add item then start checkout")
        assert decision.destination == RoutingDestination.PLAN

    def test_also_keyword_routes_to_plan(self):
        decision = self.router.route("add item to cart and also update my profile")
        assert decision.destination == RoutingDestination.PLAN

    def test_after_keyword_routes_to_plan(self):
        decision = self.router.route("after adding an item start checkout")
        assert decision.destination == RoutingDestination.PLAN


# ---------------------------------------------------------------------------
# IntentRouter — CLARIFY
# ---------------------------------------------------------------------------


class TestIntentRouterClarifyRouting:
    def setup_method(self):
        self.router = IntentRouter(
            capabilities=SAMPLE_CAPABILITIES, clarify_threshold=0.5
        )

    def test_vague_utterance_routes_to_clarify(self):
        decision = self.router.route("do the thing")
        assert decision.destination == RoutingDestination.CLARIFY
        assert decision.clarification_prompt is not None

    def test_empty_utterance_routes_to_clarify(self):
        decision = self.router.route("")
        assert decision.destination == RoutingDestination.CLARIFY

    def test_clarification_prompt_is_non_empty(self):
        decision = self.router.route("help me")
        assert decision.destination == RoutingDestination.CLARIFY
        assert len(decision.clarification_prompt) > 0


# ---------------------------------------------------------------------------
# IntentRouter — REJECT
# ---------------------------------------------------------------------------


class TestIntentRouterRejectRouting:
    def setup_method(self):
        self.router = IntentRouter(capabilities=SAMPLE_CAPABILITIES)

    def test_delete_all_is_rejected(self):
        decision = self.router.route("delete all data")
        assert decision.destination == RoutingDestination.REJECT
        assert decision.rejection_reason is not None

    def test_drop_database_is_rejected(self):
        decision = self.router.route("drop database now")
        assert decision.destination == RoutingDestination.REJECT

    def test_format_disk_is_rejected(self):
        decision = self.router.route("format disk immediately")
        assert decision.destination == RoutingDestination.REJECT


# ---------------------------------------------------------------------------
# IntentRouter — edge cases
# ---------------------------------------------------------------------------


class TestIntentRouterEdgeCases:
    def test_empty_capability_list_returns_clarify(self):
        router = IntentRouter(capabilities=[])
        decision = router.route("add item to cart")
        assert decision.destination == RoutingDestination.CLARIFY

    def test_custom_prohibited_keywords(self):
        router = IntentRouter(
            capabilities=SAMPLE_CAPABILITIES,
            prohibited_keywords=["nuclear", "destroy"],
        )
        decision = router.route("nuclear option")
        assert decision.destination == RoutingDestination.REJECT

    def test_custom_multi_step_indicators(self):
        router = IntentRouter(
            capabilities=SAMPLE_CAPABILITIES,
            multi_step_indicators=["THEN"],
        )
        decision = router.route("add item THEN checkout")
        assert decision.destination == RoutingDestination.PLAN

    def test_router_requires_capabilities_list(self):
        with pytest.raises((TypeError, IntentRouterError)):
            IntentRouter(capabilities=None)  # type: ignore[arg-type]

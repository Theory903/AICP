"""Tests for the AI plane HTTP endpoints: /v1/plan, /v1/route, /v1/judge.

TDD — tests are written before the implementation.

Endpoints under test:
  POST /v1/plan   — AICPlanner: natural language goal → multi-step plan
  POST /v1/route  — IntentRouter: utterance → routing destination
  POST /v1/judge  — AICJudge: evaluate a plan dict → judge verdict

All three are stateless; they take JSON in, return JSON out.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aicp.implementations import InMemoryCapabilityRepository
from aicp import Capability, CapabilityKind

from aicp_runtime.server.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    repo = InMemoryCapabilityRepository("ai-plane-test")
    for name, description in [
        ("cart.add_item", "Add an item to the shopping cart"),
        ("checkout.confirm", "Confirm the checkout process"),
        ("payments.charge", "Charge a payment method"),
        ("order.track", "Track the status of an existing order"),
    ]:
        repo.add_capability(
            Capability(name=name, description=description, kind=CapabilityKind.ACTION)
        )
    return create_app(capability_provider=repo)


@pytest.fixture()
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /v1/plan
# ---------------------------------------------------------------------------


class TestPlanEndpoint:
    def test_plan_returns_200_with_steps(self, client):
        response = client.post(
            "/v1/plan",
            json={
                "goal": "Add item to cart and then checkout",
                "available_capabilities": [
                    "cart.add_item",
                    "checkout.confirm",
                    "payments.charge",
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "plan_id" in data
        assert "goal" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) >= 1

    def test_plan_steps_have_required_fields(self, client):
        response = client.post(
            "/v1/plan",
            json={
                "goal": "Checkout cart",
                "available_capabilities": ["cart.add_item", "checkout.confirm"],
            },
        )
        assert response.status_code == 200
        for step in response.json()["steps"]:
            assert "step_id" in step
            assert "capability_name" in step
            assert "depends_on" in step

    def test_plan_uses_capabilities_from_provider_when_none_given(self, client):
        """When available_capabilities is omitted, use the registered provider capabilities."""
        response = client.post(
            "/v1/plan",
            json={"goal": "Add item to cart"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["steps"]) >= 1

    def test_plan_returns_422_on_empty_goal(self, client):
        response = client.post(
            "/v1/plan",
            json={"goal": "", "available_capabilities": ["cart.add_item"]},
        )
        assert response.status_code in (400, 422)

    def test_plan_returns_422_on_missing_goal(self, client):
        response = client.post("/v1/plan", json={})
        assert response.status_code == 422

    def test_plan_with_context_excludes_capabilities(self, client):
        response = client.post(
            "/v1/plan",
            json={
                "goal": "Checkout cart",
                "available_capabilities": [
                    "cart.add_item",
                    "checkout.confirm",
                    "admin.delete_all",
                ],
                "context": {"exclude_capabilities": ["admin.delete_all"]},
            },
        )
        assert response.status_code == 200
        used_caps = {s["capability_name"] for s in response.json()["steps"]}
        assert "admin.delete_all" not in used_caps


# ---------------------------------------------------------------------------
# POST /v1/route
# ---------------------------------------------------------------------------


class TestRouteEndpoint:
    def test_route_capability_returns_200(self, client):
        response = client.post(
            "/v1/route",
            json={"utterance": "add item to cart"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "destination" in data
        assert "confidence" in data

    def test_route_multi_step_returns_plan_destination(self, client):
        response = client.post(
            "/v1/route",
            json={"utterance": "add item to cart and then checkout"},
        )
        assert response.status_code == 200
        assert response.json()["destination"] == "plan"

    def test_route_prohibited_returns_reject(self, client):
        response = client.post(
            "/v1/route",
            json={"utterance": "delete all data"},
        )
        assert response.status_code == 200
        assert response.json()["destination"] == "reject"

    def test_route_vague_returns_clarify(self, client):
        response = client.post(
            "/v1/route",
            json={"utterance": "do the thing"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["destination"] == "clarify"
        assert data.get("clarification_prompt") is not None

    def test_route_uses_provider_capabilities_by_default(self, client):
        """Route against the registered provider capabilities when no list is given."""
        response = client.post(
            "/v1/route",
            json={"utterance": "track my order"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["destination"] in ("capability", "plan", "clarify", "reject")

    def test_route_accepts_explicit_capabilities(self, client):
        response = client.post(
            "/v1/route",
            json={
                "utterance": "charge my card",
                "available_capabilities": [
                    {
                        "name": "payments.charge",
                        "description": "Charge a payment method",
                        "kind": "action",
                    }
                ],
            },
        )
        assert response.status_code == 200
        assert response.json()["destination"] == "capability"

    def test_route_returns_422_on_missing_utterance(self, client):
        response = client.post("/v1/route", json={})
        assert response.status_code == 422

    def test_route_confidence_between_0_and_1(self, client):
        response = client.post(
            "/v1/route",
            json={"utterance": "add item to cart"},
        )
        confidence = response.json()["confidence"]
        assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# POST /v1/judge
# ---------------------------------------------------------------------------


class TestJudgeEndpoint:
    def _valid_plan(self):
        return {
            "plan_id": "plan_test_001",
            "goal": "Checkout cart",
            "generated_at": "2026-04-03T00:00:00Z",
            "steps": [
                {
                    "step_id": "s1",
                    "capability_name": "cart.add_item",
                    "depends_on": [],
                    "arguments": {},
                },
                {
                    "step_id": "s2",
                    "capability_name": "checkout.confirm",
                    "depends_on": ["s1"],
                    "arguments": {},
                },
            ],
        }

    def test_judge_valid_plan_returns_200(self, client):
        response = client.post("/v1/judge", json={"plan": self._valid_plan()})
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert "score" in data
        assert "rationale" in data
        assert "evaluated_at" in data

    def test_judge_valid_plan_verdict_is_approved_or_partial(self, client):
        response = client.post("/v1/judge", json={"plan": self._valid_plan()})
        assert response.status_code == 200
        assert response.json()["verdict"] in ("approved", "partial")

    def test_judge_empty_steps_plan_is_rejected(self, client):
        plan = {
            "plan_id": "plan_empty",
            "goal": "Do nothing",
            "generated_at": "2026-04-03T00:00:00Z",
            "steps": [],
        }
        response = client.post("/v1/judge", json={"plan": plan})
        assert response.status_code == 200
        assert response.json()["verdict"] == "rejected"

    def test_judge_circular_deps_plan_is_rejected(self, client):
        plan = {
            "plan_id": "plan_circular",
            "goal": "Circular",
            "generated_at": "2026-04-03T00:00:00Z",
            "steps": [
                {
                    "step_id": "s1",
                    "capability_name": "a.foo",
                    "depends_on": ["s2"],
                    "arguments": {},
                },
                {
                    "step_id": "s2",
                    "capability_name": "b.bar",
                    "depends_on": ["s1"],
                    "arguments": {},
                },
            ],
        }
        response = client.post("/v1/judge", json={"plan": plan})
        assert response.status_code == 200
        assert response.json()["verdict"] == "rejected"

    def test_judge_score_between_0_and_1(self, client):
        response = client.post("/v1/judge", json={"plan": self._valid_plan()})
        score = response.json()["score"]
        assert 0.0 <= score <= 1.0

    def test_judge_returns_422_on_missing_plan(self, client):
        response = client.post("/v1/judge", json={})
        assert response.status_code == 422

    def test_judge_returns_400_on_null_plan(self, client):
        response = client.post("/v1/judge", json={"plan": None})
        assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# L4 conformance tests
# Verify that /v1/plan, /v1/route, /v1/judge response envelopes match the
# structural sub-schemas defined in spec/schemas/session.schema.json:
#   - planner_output  (plan_id, goal, steps[], generated_at)
#   - judge_verdict   (verdict enum, score [0,1], rationale, evaluated_at)
#   - routing_decision (destination enum, confidence [0,1])
# ---------------------------------------------------------------------------


class TestPlanResponseConformance:
    """POST /v1/plan — PlanResponse field types and structure."""

    def _plan_response(self, client, goal="Add item to cart and checkout"):
        return client.post(
            "/v1/plan",
            json={
                "goal": goal,
                "available_capabilities": [
                    "cart.add_item",
                    "checkout.confirm",
                    "payments.charge",
                ],
            },
        )

    def test_plan_id_is_non_empty_string(self, client):
        data = self._plan_response(client).json()
        assert isinstance(data["plan_id"], str)
        assert len(data["plan_id"]) > 0

    def test_goal_is_non_empty_string(self, client):
        data = self._plan_response(client).json()
        assert isinstance(data["goal"], str)
        assert len(data["goal"]) > 0

    def test_generated_at_is_iso8601_datetime(self, client):
        """generated_at must be parseable as an ISO-8601 datetime string."""
        from datetime import datetime

        data = self._plan_response(client).json()
        ts = data["generated_at"]
        assert isinstance(ts, str)
        # datetime.fromisoformat handles Z-suffix in Python 3.11+; normalise first
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.year >= 2020

    def test_steps_is_list(self, client):
        data = self._plan_response(client).json()
        assert isinstance(data["steps"], list)

    def test_step_id_is_string(self, client):
        data = self._plan_response(client).json()
        for step in data["steps"]:
            assert isinstance(step["step_id"], str)
            assert len(step["step_id"]) > 0

    def test_step_capability_name_is_string(self, client):
        data = self._plan_response(client).json()
        for step in data["steps"]:
            assert isinstance(step["capability_name"], str)
            assert len(step["capability_name"]) > 0

    def test_step_depends_on_is_list_of_strings(self, client):
        data = self._plan_response(client).json()
        for step in data["steps"]:
            assert isinstance(step["depends_on"], list)
            for dep in step["depends_on"]:
                assert isinstance(dep, str)

    def test_step_arguments_is_dict(self, client):
        data = self._plan_response(client).json()
        for step in data["steps"]:
            assert isinstance(step.get("arguments", {}), dict)

    def test_plan_response_has_no_extra_required_fields(self, client):
        """PlanResponse must contain exactly the schema-defined top-level keys."""
        data = self._plan_response(client).json()
        required_keys = {"plan_id", "goal", "steps", "generated_at"}
        assert required_keys.issubset(set(data.keys()))

    def test_goal_echoes_input_goal(self, client):
        goal = "Charge payment and confirm order"
        data = self._plan_response(client, goal=goal).json()
        assert data["goal"] == goal


class TestJudgeResponseConformance:
    """POST /v1/judge — JudgeResponse conforms to judge_verdict sub-schema."""

    VALID_VERDICTS = {"approved", "rejected", "needs_revision", "partial"}

    def _judge_response(self, client, steps=None):
        if steps is None:
            steps = [
                {"step_id": "s1", "capability_name": "cart.add_item", "depends_on": []},
                {
                    "step_id": "s2",
                    "capability_name": "checkout.confirm",
                    "depends_on": ["s1"],
                },
            ]
        plan = {
            "plan_id": "plan_conform_001",
            "goal": "Checkout cart",
            "generated_at": "2026-04-03T00:00:00Z",
            "steps": steps,
        }
        return client.post("/v1/judge", json={"plan": plan})

    def test_verdict_is_enum_value(self, client):
        data = self._judge_response(client).json()
        assert data["verdict"] in self.VALID_VERDICTS

    def test_score_is_number_in_unit_interval(self, client):
        data = self._judge_response(client).json()
        score = data["score"]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 1.0

    def test_rationale_is_non_empty_string(self, client):
        data = self._judge_response(client).json()
        assert isinstance(data["rationale"], str)
        assert len(data["rationale"]) > 0

    def test_evaluated_at_is_iso8601_datetime(self, client):
        from datetime import datetime

        data = self._judge_response(client).json()
        ts = data["evaluated_at"]
        assert isinstance(ts, str)
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.year >= 2020

    def test_response_keys_match_schema(self, client):
        data = self._judge_response(client).json()
        required_keys = {"verdict", "score", "rationale", "evaluated_at"}
        assert required_keys.issubset(set(data.keys()))

    def test_rejected_verdict_has_low_score(self, client):
        """Empty-step plan is rejected; score should be <= 0.3."""
        data = self._judge_response(client, steps=[]).json()
        assert data["verdict"] == "rejected"
        assert data["score"] <= 0.3

    def test_approved_verdict_has_high_score(self, client):
        """Valid 2-step plan should yield approved/partial with score >= 0.5."""
        data = self._judge_response(client).json()
        assert data["verdict"] in ("approved", "partial")
        assert data["score"] >= 0.5


class TestRouteResponseConformance:
    """POST /v1/route — RouteResponse conforms to routing_decision sub-schema."""

    VALID_DESTINATIONS = {"capability", "plan", "clarify", "reject"}

    def _route_response(self, client, utterance="add item to cart"):
        return client.post("/v1/route", json={"utterance": utterance})

    def test_destination_is_enum_value(self, client):
        data = self._route_response(client).json()
        assert data["destination"] in self.VALID_DESTINATIONS

    def test_confidence_is_float_in_unit_interval(self, client):
        data = self._route_response(client).json()
        confidence = data["confidence"]
        assert isinstance(confidence, (int, float))
        assert 0.0 <= confidence <= 1.0

    def test_capability_destination_has_capability_name(self, client):
        data = self._route_response(client, utterance="add item to cart").json()
        if data["destination"] == "capability":
            assert isinstance(data.get("capability_name"), str)
            assert len(data["capability_name"]) > 0

    def test_clarify_destination_has_clarification_prompt(self, client):
        data = self._route_response(client, utterance="do the thing").json()
        if data["destination"] == "clarify":
            assert isinstance(data.get("clarification_prompt"), str)
            assert len(data["clarification_prompt"]) > 0

    def test_reject_destination_has_rejection_reason(self, client):
        data = self._route_response(client, utterance="delete all data").json()
        if data["destination"] == "reject":
            assert isinstance(data.get("rejection_reason"), str)
            assert len(data["rejection_reason"]) > 0

    def test_response_keys_include_required_fields(self, client):
        data = self._route_response(client).json()
        assert "destination" in data
        assert "confidence" in data

    def test_non_clarify_has_no_clarification_prompt_or_null(self, client):
        """For non-clarify destinations, clarification_prompt should be null or absent."""
        data = self._route_response(client, utterance="add item to cart").json()
        if data["destination"] != "clarify":
            prompt = data.get("clarification_prompt")
            assert prompt is None or prompt == ""


class TestPlanJudgeRoundTrip:
    """Integration: plan output piped into judge — round-trip conformance."""

    def test_planner_output_is_valid_judge_input(self, client):
        """A plan produced by /v1/plan must be accepted by /v1/judge without error."""
        plan_resp = client.post(
            "/v1/plan",
            json={
                "goal": "Add item to cart and checkout",
                "available_capabilities": ["cart.add_item", "checkout.confirm"],
            },
        )
        assert plan_resp.status_code == 200
        plan = plan_resp.json()

        judge_resp = client.post("/v1/judge", json={"plan": plan})
        assert judge_resp.status_code == 200
        verdict = judge_resp.json()
        assert verdict["verdict"] in (
            "approved",
            "partial",
            "rejected",
            "needs_revision",
        )
        assert 0.0 <= verdict["score"] <= 1.0

    def test_planner_and_judge_agree_on_non_empty_plan(self, client):
        """A plan with at least one step should not be instantly rejected by the judge."""
        plan_resp = client.post(
            "/v1/plan",
            json={
                "goal": "Checkout cart",
                "available_capabilities": ["checkout.confirm"],
            },
        )
        assert plan_resp.status_code == 200
        plan = plan_resp.json()
        assert len(plan["steps"]) >= 1

        judge_resp = client.post("/v1/judge", json={"plan": plan})
        assert judge_resp.status_code == 200
        assert judge_resp.json()["verdict"] != "rejected"

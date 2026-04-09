"""Tests for the AI Planner module (TDD — write tests first)."""

from __future__ import annotations

import pytest

from aicp_runtime.ai.planner import (
    PlanStep,
    PlannerOutput,
    AICPlanner,
    PlannerError,
)


class TestPlanStep:
    def test_plan_step_minimal(self):
        step = PlanStep(step_id="s1", capability_name="cart.add_item")
        assert step.step_id == "s1"
        assert step.capability_name == "cart.add_item"
        assert step.depends_on == []
        assert step.arguments == {}
        assert step.rationale is None

    def test_plan_step_with_deps_and_args(self):
        step = PlanStep(
            step_id="s2",
            capability_name="payments.charge",
            arguments={"amount": 42.50},
            depends_on=["s1"],
            rationale="Charge after checkout confirmed",
        )
        assert step.depends_on == ["s1"]
        assert step.arguments["amount"] == 42.50
        assert step.rationale == "Charge after checkout confirmed"

    def test_plan_step_serialises_to_dict(self):
        step = PlanStep(step_id="s1", capability_name="cart.add_item")
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["capability_name"] == "cart.add_item"
        assert "depends_on" in d


class TestPlannerOutput:
    def test_planner_output_creation(self):
        steps = [
            PlanStep(step_id="s1", capability_name="cart.add_item"),
            PlanStep(
                step_id="s2", capability_name="checkout.confirm", depends_on=["s1"]
            ),
        ]
        output = PlannerOutput(
            goal="Place food order",
            steps=steps,
        )
        assert output.goal == "Place food order"
        assert len(output.steps) == 2
        assert output.plan_id is not None  # auto-generated
        assert output.generated_at is not None

    def test_planner_output_serialises_to_dict(self):
        output = PlannerOutput(
            goal="Test goal",
            steps=[PlanStep(step_id="s1", capability_name="test.action")],
        )
        d = output.to_dict()
        assert d["goal"] == "Test goal"
        assert len(d["steps"]) == 1
        assert "plan_id" in d
        assert "generated_at" in d

    def test_planner_output_conforms_to_session_schema(self):
        """PlannerOutput dict must conform to the session.schema.json planner_output sub-schema."""
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator

        # packages/runtime/tests/ai/ -> packages/runtime/tests/ -> packages/runtime/ -> packages/ -> AICP/
        schema_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "aicp-core"
            / "spec"
            / "schemas"
            / "session.schema.json"
        )
        with open(schema_path) as f:
            full_schema = json.load(f)

        planner_sub_schema = full_schema["properties"]["planner_output"]
        validator = Draft202012Validator(planner_sub_schema)

        output = PlannerOutput(
            goal="Place food order",
            steps=[PlanStep(step_id="s1", capability_name="cart.add_item")],
        )
        errors = list(validator.iter_errors(output.to_dict()))
        assert not errors, f"PlannerOutput does not conform to schema: {errors}"


class TestAICPlanner:
    def setup_method(self):
        self.planner = AICPlanner()

    def test_planner_generates_plan_from_goal(self):
        """Given a goal and a list of available capabilities, produce a plan."""
        available = [
            "cart.add_item",
            "checkout.confirm",
            "payments.charge",
            "order.track",
        ]
        output = self.planner.plan(
            goal="Place a food order and track delivery",
            available_capabilities=available,
        )
        assert isinstance(output, PlannerOutput)
        assert output.goal == "Place a food order and track delivery"
        assert len(output.steps) >= 1

    def test_planner_steps_use_available_capabilities(self):
        """All plan steps must use capabilities from the available set."""
        available = ["cart.add_item", "checkout.confirm", "payments.charge"]
        output = self.planner.plan(
            goal="Checkout the cart",
            available_capabilities=available,
        )
        for step in output.steps:
            assert step.capability_name in available, (
                f"Step {step.step_id} uses unknown capability {step.capability_name!r}"
            )

    def test_planner_respects_dependency_order(self):
        """Steps with depends_on must reference step_ids that appear earlier."""
        available = ["checkout.confirm", "payments.charge"]
        output = self.planner.plan(
            goal="Confirm checkout then charge",
            available_capabilities=available,
        )
        step_ids_seen: set[str] = set()
        for step in output.steps:
            for dep in step.depends_on:
                assert dep in step_ids_seen, (
                    f"Step {step.step_id} depends on {dep!r} which hasn't been defined yet"
                )
            step_ids_seen.add(step.step_id)

    def test_planner_raises_on_empty_capabilities(self):
        with pytest.raises(PlannerError, match="no capabilities"):
            self.planner.plan(goal="Do something", available_capabilities=[])

    def test_planner_raises_on_empty_goal(self):
        with pytest.raises(PlannerError, match="goal"):
            self.planner.plan(goal="", available_capabilities=["cart.add_item"])

    def test_planner_single_capability_goal(self):
        """A goal matching a single capability produces a one-step plan."""
        output = self.planner.plan(
            goal="Add item to cart",
            available_capabilities=["cart.add_item"],
        )
        assert len(output.steps) == 1
        assert output.steps[0].capability_name == "cart.add_item"

    def test_planner_output_has_unique_step_ids(self):
        available = ["cart.add_item", "checkout.confirm", "payments.charge"]
        output = self.planner.plan(
            goal="Full checkout flow", available_capabilities=available
        )
        step_ids = [s.step_id for s in output.steps]
        assert len(step_ids) == len(set(step_ids)), "Step IDs must be unique"

    def test_plan_with_context_filters_capabilities(self):
        """Context hints narrow the capability set used in the plan."""
        available = [
            "cart.add_item",
            "checkout.confirm",
            "payments.charge",
            "admin.delete_all",
        ]
        output = self.planner.plan(
            goal="Checkout the cart",
            available_capabilities=available,
            context={"exclude_capabilities": ["admin.delete_all"]},
        )
        used = {s.capability_name for s in output.steps}
        assert "admin.delete_all" not in used

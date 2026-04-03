"""Tests for the AI Judge module (TDD — tests first)."""

from __future__ import annotations

import pytest

from aicp_runtime.ai.judge import (
    JudgeVerdict,
    JudgeResult,
    AICJudge,
    JudgeError,
)
from aicp_runtime.ai.planner import AICPlanner, PlannerOutput


def _make_plan(goal: str = "Checkout", caps: list[str] | None = None) -> PlannerOutput:
    caps = caps or ["cart.add_item", "checkout.confirm", "payments.charge"]
    return AICPlanner().plan(goal=goal, available_capabilities=caps)


class TestJudgeVerdict:
    def test_verdict_enum_values(self):
        assert JudgeVerdict.APPROVED.value == "approved"
        assert JudgeVerdict.REJECTED.value == "rejected"
        assert JudgeVerdict.NEEDS_REVISION.value == "needs_revision"
        assert JudgeVerdict.PARTIAL.value == "partial"


class TestJudgeResult:
    def test_judge_result_creation(self):
        result = JudgeResult(
            verdict=JudgeVerdict.APPROVED,
            score=0.9,
            rationale="Plan is sound",
        )
        assert result.verdict == JudgeVerdict.APPROVED
        assert result.score == 0.9
        assert result.rationale == "Plan is sound"
        assert result.evaluated_at is not None

    def test_judge_result_score_clamped(self):
        """Score must be in [0, 1]."""
        with pytest.raises(ValueError, match="score"):
            JudgeResult(verdict=JudgeVerdict.APPROVED, score=1.5, rationale="x")

        with pytest.raises(ValueError, match="score"):
            JudgeResult(verdict=JudgeVerdict.APPROVED, score=-0.1, rationale="x")

    def test_judge_result_to_dict(self):
        result = JudgeResult(
            verdict=JudgeVerdict.APPROVED,
            score=0.85,
            rationale="Looks good",
        )
        d = result.to_dict()
        assert d["verdict"] == "approved"
        assert d["score"] == 0.85
        assert "rationale" in d
        assert "evaluated_at" in d

    def test_judge_result_conforms_to_session_schema(self):
        """JudgeResult dict must conform to session.schema.json judge_verdict sub-schema."""
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator

        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "spec" / "schemas" / "session.schema.json"
        )
        with open(schema_path) as f:
            full_schema = json.load(f)

        sub_schema = full_schema["properties"]["judge_verdict"]
        validator = Draft202012Validator(sub_schema)

        result = JudgeResult(
            verdict=JudgeVerdict.APPROVED,
            score=0.91,
            rationale="Plan is coherent",
        )
        errors = list(validator.iter_errors(result.to_dict()))
        assert not errors, f"JudgeResult does not conform to schema: {errors}"


class TestAICJudge:
    def setup_method(self):
        self.judge = AICJudge()

    def test_valid_plan_gets_approved_or_partial(self):
        plan = _make_plan()
        result = self.judge.evaluate(plan)
        assert isinstance(result, JudgeResult)
        assert result.verdict in (JudgeVerdict.APPROVED, JudgeVerdict.PARTIAL)
        assert 0.0 <= result.score <= 1.0

    def test_empty_steps_plan_gets_rejected(self):
        """A plan with no steps should be rejected."""
        plan = PlannerOutput(goal="Do nothing", steps=[])
        result = self.judge.evaluate(plan)
        assert result.verdict == JudgeVerdict.REJECTED
        assert result.score < 0.5

    def test_circular_dependency_detected(self):
        """A plan with a circular dep gets REJECTED."""
        from aicp_runtime.ai.planner import PlanStep
        steps = [
            PlanStep(step_id="s1", capability_name="a.foo", depends_on=["s2"]),
            PlanStep(step_id="s2", capability_name="b.bar", depends_on=["s1"]),
        ]
        plan = PlannerOutput(goal="Circular", steps=steps)
        result = self.judge.evaluate(plan)
        assert result.verdict == JudgeVerdict.REJECTED

    def test_duplicate_step_ids_detected(self):
        """A plan with duplicate step IDs should be rejected."""
        from aicp_runtime.ai.planner import PlanStep
        steps = [
            PlanStep(step_id="s1", capability_name="a.foo"),
            PlanStep(step_id="s1", capability_name="b.bar"),
        ]
        plan = PlannerOutput(goal="Dupe IDs", steps=steps)
        result = self.judge.evaluate(plan)
        assert result.verdict == JudgeVerdict.REJECTED

    def test_raises_on_none_plan(self):
        with pytest.raises(JudgeError, match="plan"):
            self.judge.evaluate(None)  # type: ignore[arg-type]

    def test_result_includes_rationale(self):
        plan = _make_plan()
        result = self.judge.evaluate(plan)
        assert result.rationale and len(result.rationale) > 0

    def test_score_reflects_step_count(self):
        """A single-step plan for a trivial goal should score reasonably."""
        plan = AICPlanner().plan(
            goal="Add item to cart",
            available_capabilities=["cart.add_item"],
        )
        result = self.judge.evaluate(plan)
        assert result.score > 0.0

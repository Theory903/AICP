"""AI Judge for AICP.

Evaluates a PlannerOutput for structural correctness, coherence, and
policy-readiness.  Returns a JudgeResult with a verdict, score, and rationale.

This is the reference (rule-based) implementation.  A production deployment
can swap in an LLM call; the interface is stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aicp_runtime.ai.planner import PlannerOutput


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------


class JudgeVerdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------


@dataclass
class JudgeResult:
    """The verdict produced by the AI Judge."""

    verdict: JudgeVerdict
    score: float
    rationale: str
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "rationale": self.rationale,
            "evaluated_at": self.evaluated_at,
        }


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class JudgeError(Exception):
    """Raised when the judge cannot evaluate (e.g. None input)."""


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def _has_cycle(steps: list) -> bool:  # type: ignore[type-arg]
    """Return True if the steps dependency graph contains a cycle."""
    ids = {s.step_id for s in steps}
    graph: dict[str, list[str]] = {s.step_id: list(s.depends_on) for s in steps}

    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node not in ids:
            return False  # unknown dep — handled elsewhere
        visited.add(node)
        in_stack.add(node)
        for neighbour in graph.get(node, []):
            if neighbour not in visited:
                if dfs(neighbour):
                    return True
            elif neighbour in in_stack:
                return True
        in_stack.discard(node)
        return False

    for step_id in list(ids):
        if step_id not in visited:
            if dfs(step_id):
                return True
    return False


class AICJudge:
    """Rule-based AI Judge.

    Scoring rubric (each component contributes to the final score):
    - Has at least one step                (+0.3)
    - No duplicate step IDs               (+0.2)
    - No circular dependencies            (+0.2)
    - All dep references are valid step IDs (+0.2)
    - Goal is non-empty                   (+0.1)
    """

    def evaluate(self, plan: PlannerOutput) -> JudgeResult:  # type: ignore[return]
        if plan is None:
            raise JudgeError("plan must not be None")

        issues: list[str] = []
        score = 0.0

        # 1. Has steps
        if plan.steps:
            score += 0.3
        else:
            issues.append("Plan has no steps.")

        # Checks 2–4 only make sense when there are steps.
        if plan.steps:
            # 2. No duplicate step IDs
            step_ids = [s.step_id for s in plan.steps]
            if len(step_ids) == len(set(step_ids)):
                score += 0.2
            else:
                issues.append("Duplicate step IDs detected.")

            # 3. No circular dependencies
            if not _has_cycle(plan.steps):
                score += 0.2
            else:
                issues.append("Circular dependency detected in plan.")

            # 4. All dependency references are valid step IDs
            valid_ids = set(step_ids)
            bad_deps = [
                f"{s.step_id} -> {dep}"
                for s in plan.steps
                for dep in s.depends_on
                if dep not in valid_ids
            ]
            if not bad_deps:
                score += 0.2
            else:
                issues.append(f"Unknown dependency references: {bad_deps}")
        else:
            step_ids = []

        # 5. Goal is non-empty
        if plan.goal and plan.goal.strip():
            score += 0.1
        else:
            issues.append("Plan goal is empty.")

        # Determine verdict
        critical = any(
            kw in " ".join(issues)
            for kw in ("Circular", "Duplicate", "no steps")
        )

        if critical or score < 0.5:
            verdict = JudgeVerdict.REJECTED
        elif issues:
            verdict = JudgeVerdict.NEEDS_REVISION if score < 0.8 else JudgeVerdict.PARTIAL
        else:
            verdict = JudgeVerdict.APPROVED

        rationale = "Plan is coherent and ready for execution." if not issues else " ".join(issues)

        return JudgeResult(verdict=verdict, score=round(score, 4), rationale=rationale)

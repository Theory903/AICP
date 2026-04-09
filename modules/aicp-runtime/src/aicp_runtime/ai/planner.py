"""AI Planner for AICP.

Given a natural-language goal and a set of available capability names, the
AICPlanner produces a PlannerOutput: an ordered, dependency-linked sequence of
PlanStep objects.

This is the reference (rule-based / heuristic) implementation.  A production
deployment would swap in an LLM call here; the interface is stable.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


@dataclass
class PlanStep:
    """A single step in an AI-generated plan."""

    step_id: str
    capability_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step_id": self.step_id,
            "capability_name": self.capability_name,
            "arguments": self.arguments,
            "depends_on": self.depends_on,
        }
        if self.rationale is not None:
            d["rationale"] = self.rationale
        return d


@dataclass
class PlannerOutput:
    """The full output of a planning pass."""

    goal: str
    steps: list[PlanStep]
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "plan_id": self.plan_id,
            "steps": [s.to_dict() for s in self.steps],
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PlannerError(Exception):
    """Raised when planning cannot proceed."""


# ---------------------------------------------------------------------------
# Heuristic planner implementation
# ---------------------------------------------------------------------------

# Canonical ordering hints: earlier prefixes should come before later ones.
_STAGE_PREFIXES: list[str] = [
    "cart",
    "basket",
    "checkout",
    "payment",
    "payments",
    "order",
    "orders",
    "shipping",
    "notification",
    "notify",
    "track",
    "tracking",
    "admin",
]


def _stage_rank(cap_name: str) -> int:
    """Return the pipeline stage rank of a capability (lower = earlier)."""
    prefix = cap_name.split(".")[0].lower()
    try:
        return _STAGE_PREFIXES.index(prefix)
    except ValueError:
        return len(_STAGE_PREFIXES)  # unknown = last


def _tokenise(text: str) -> set[str]:
    """Extract lowercase word tokens from a string."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _capability_relevance(cap_name: str, goal_tokens: set[str]) -> float:
    """Score how relevant a capability name is to a goal (0–1)."""
    cap_tokens = _tokenise(cap_name)
    if not cap_tokens:
        return 0.0
    overlap = cap_tokens & goal_tokens
    return len(overlap) / max(len(cap_tokens), len(goal_tokens))


class AICPlanner:
    """Rule-based / heuristic AI Planner.

    The planner:
    1. Filters out capabilities excluded by context.
    2. Scores each capability for relevance to the goal.
    3. Selects the relevant subset (or all caps if none score above threshold).
    4. Orders them by pipeline stage.
    5. Links each step to the previous one via `depends_on`.
    """

    RELEVANCE_THRESHOLD: float = 0.1

    def plan(
        self,
        goal: str,
        available_capabilities: list[str],
        context: dict[str, Any] | None = None,
    ) -> PlannerOutput:
        """Generate a plan.

        Args:
            goal: Natural-language description of what to accomplish.
            available_capabilities: Names of capabilities the planner may use.
            context: Optional hints, e.g. ``{"exclude_capabilities": [...]}``.

        Returns:
            PlannerOutput with ordered, dependency-linked PlanStep objects.

        Raises:
            PlannerError: If goal is empty or no capabilities are available.
        """
        if not goal or not goal.strip():
            raise PlannerError("goal must not be empty")
        if not available_capabilities:
            raise PlannerError("no capabilities available for planning")

        ctx = context or {}

        # 1. Apply exclusions.
        excluded: set[str] = set(ctx.get("exclude_capabilities", []))
        caps = [c for c in available_capabilities if c not in excluded]
        if not caps:
            raise PlannerError("no capabilities available after applying exclusions")

        # 2. Score relevance.
        goal_tokens = _tokenise(goal)
        scored = [(cap, _capability_relevance(cap, goal_tokens)) for cap in caps]

        # 3. Select relevant caps (above threshold), or fall back to all.
        relevant = [cap for cap, score in scored if score >= self.RELEVANCE_THRESHOLD]
        if not relevant:
            relevant = caps  # fallback: use all available

        # 4. Sort by pipeline stage.
        relevant.sort(key=_stage_rank)

        # 5. Build steps with linear dependency chain.
        steps: list[PlanStep] = []
        prev_id: str | None = None
        for i, cap in enumerate(relevant):
            step_id = f"step_{i + 1}"
            depends_on = [prev_id] if prev_id else []
            steps.append(
                PlanStep(
                    step_id=step_id,
                    capability_name=cap,
                    depends_on=depends_on,
                )
            )
            prev_id = step_id

        return PlannerOutput(goal=goal, steps=steps)

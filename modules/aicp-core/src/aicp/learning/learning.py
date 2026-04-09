import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aicp.learning.domains import Benchmark, BenchmarkResult, DomainCategory, DomainPack


class DriftType(str, Enum):
    CAPABILITY_USAGE = "capability_usage"
    POLICY_EFFECTIVENESS = "policy_effectiveness"
    WORKFLOW_PATTERNS = "workflow_patterns"
    ERROR_RATES = "error_rates"
    RESPONSE_TIMES = "response_times"


class AutonomyLevel(str, Enum):
    CONSTRAINED = "constrained"
    GUIDED = "guided"
    AUTONOMOUS = "autonomous"
    FULL = "full"


class Skill(BaseModel):
    id: str = Field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    capability_names: list[str] = Field(default_factory=list)
    workflow_ids: list[str] = Field(default_factory=list)
    success_rate: float = 0.0
    usage_count: int = 0
    avg_execution_time_ms: float = 0.0
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MinedSkill(BaseModel):
    id: str = Field(default_factory=lambda: f"mined_{uuid.uuid4().hex[:8]}")
    source_capabilities: list[str]
    source_workflows: list[str]
    pattern_type: str
    confidence: float
    suggested_name: str
    suggested_description: str
    discovered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class LearnedPolicy(BaseModel):
    id: str = Field(default_factory=lambda: f"learn_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    conditions: dict[str, Any]
    effect: str
    confidence: float
    training_data_size: int
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DriftDetection(BaseModel):
    id: str = Field(default_factory=lambda: f"drift_{uuid.uuid4().hex[:8]}")
    drift_type: DriftType
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    severity: str
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    recommendations: list[str] = Field(default_factory=list)


class AutonomyCalibration(BaseModel):
    agent_id: str
    autonomy_level: AutonomyLevel
    trust_score: float
    last_calibrated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    recommendations: list[str] = Field(default_factory=list)


class LearningService:
    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._mined_skills: dict[str, MinedSkill] = {}
        self._learned_policies: dict[str, LearnedPolicy] = {}
        self._drift_detections: dict[str, DriftDetection] = {}
        self._benchmark_results: list[BenchmarkResult] = []
        self._domain_packs: dict[str, DomainPack] = {}
        self._benchmarks: dict[str, Benchmark] = {}
        self._skill_history: dict[str, list[dict[str, Any]]] = {}

    def add_domain_pack(self, pack: DomainPack) -> None:
        self._domain_packs[pack.id] = pack

    def get_domain_pack(self, pack_id: str) -> DomainPack | None:
        return self._domain_packs.get(pack_id)

    def get_domain_packs(self, category: DomainCategory | None = None) -> list[DomainPack]:
        if category:
            return [p for p in self._domain_packs.values() if p.category == category]
        return list(self._domain_packs.values())

    def add_benchmark(self, benchmark: Benchmark) -> None:
        self._benchmarks[benchmark.id] = benchmark

    def get_benchmark(self, benchmark_id: str) -> Benchmark | None:
        return self._benchmarks.get(benchmark_id)

    def get_all_benchmarks(self) -> list[Benchmark]:
        return list(self._benchmarks.values())

    def record_benchmark_result(self, result: BenchmarkResult) -> None:
        self._benchmark_results.append(result)

    def get_benchmark_results(self, benchmark_id: str | None = None) -> list[BenchmarkResult]:
        if benchmark_id:
            return [b for b in self._benchmark_results if b.benchmark_id == benchmark_id]
        return self._benchmark_results[-100:]

    def add_skill(self, skill: Skill) -> None:
        self._skills[skill.id] = skill

    def get_skill(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    def get_all_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def update_skill_metrics(self, skill_id: str, success: bool, execution_time_ms: float) -> None:
        skill = self._skills.get(skill_id)
        if not skill:
            return

        skill.usage_count += 1
        total_time = skill.avg_execution_time_ms * (skill.usage_count - 1)
        skill.avg_execution_time_ms = (total_time + execution_time_ms) / skill.usage_count

        if success:
            current_wins = skill.success_rate * (skill.usage_count - 1)
            skill.success_rate = (current_wins + 1) / skill.usage_count
        else:
            current_wins = skill.success_rate * (skill.usage_count - 1)
            skill.success_rate = current_wins / skill.usage_count

    def add_mined_skill(self, mined: MinedSkill) -> None:
        self._mined_skills[mined.id] = mined

    def get_mined_skills(self, min_confidence: float = 0.0) -> list[MinedSkill]:
        return [s for s in self._mined_skills.values() if s.confidence >= min_confidence]

    def add_learned_policy(self, policy: LearnedPolicy) -> None:
        self._learned_policies[policy.id] = policy

    def get_learned_policies(self) -> list[LearnedPolicy]:
        return list(self._learned_policies.values())

    def record_drift(self, drift: DriftDetection) -> None:
        self._drift_detections[drift.id] = drift

    def get_drift_detections(self, drift_type: DriftType | None = None) -> list[DriftDetection]:
        if drift_type:
            return [d for d in self._drift_detections.values() if d.drift_type == drift_type]
        return list(self._drift_detections.values())

    def calibrate_autonomy(self, agent_id: str, metrics: dict[str, float]) -> AutonomyCalibration:
        trust_score = 0.5

        if metrics.get("success_rate", 0) > 0.9:
            trust_score += 0.2
        if metrics.get("approval_rate", 0) > 0.95:
            trust_score += 0.1
        if metrics.get("error_rate", 1) < 0.05:
            trust_score += 0.1

        trust_score = min(1.0, trust_score)

        if trust_score >= 0.9:
            level = AutonomyLevel.FULL
        elif trust_score >= 0.7:
            level = AutonomyLevel.AUTONOMOUS
        elif trust_score >= 0.5:
            level = AutonomyLevel.GUIDED
        else:
            level = AutonomyLevel.CONSTRAINED

        return AutonomyCalibration(
            agent_id=agent_id,
            autonomy_level=level,
            trust_score=trust_score
        )


class SkillMiner:
    def __init__(self, learning_service: LearningService):
        self._service = learning_service

    def mine_from_capabilities(self, capabilities: list[dict[str, Any]]) -> list[MinedSkill]:
        mined = []

        similar_caps = self._find_similar_capabilities(capabilities)
        if len(similar_caps) >= 3:
            mined.append(MinedSkill(
                source_capabilities=[c.get("name", "") for c in similar_caps],
                source_workflows=[],
                pattern_type="capability_grouping",
                confidence=0.85,
                suggested_name="Composite Action Handler",
                suggested_description="Handles multiple related capabilities"
            ))

        return mined

    def _find_similar_capabilities(self, capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(capabilities) < 3:
            return capabilities[:3]
        return capabilities[:5]

    def mine_from_workflows(self, workflows: list[dict[str, Any]]) -> list[MinedSkill]:
        mined = []

        for wf in workflows:
            steps = wf.get("steps", [])
            if len(steps) >= 2:
                cap_names = [s.get("capability_name", "") for s in steps]
                mined.append(MinedSkill(
                    source_capabilities=cap_names,
                    source_workflows=[wf.get("name", "")],
                    pattern_type="workflow_pattern",
                    confidence=0.9,
                    suggested_name=f"Workflow: {wf.get('name', 'unnamed')}",
                    suggested_description=f"Multi-step workflow with {len(steps)} steps"
                ))

        return mined


class PolicyLearner:
    def __init__(self, learning_service: LearningService):
        self._service = learning_service

    def learn_from_execution(
        self,
        capability_name: str,
        approval_required: bool,
        was_approved: bool,
    ) -> LearnedPolicy | None:
        if not approval_required:
            return None

        return LearnedPolicy(
            name=f"Auto-approve {capability_name}",
            description=f"Auto-approve {capability_name} based on approval history",
            conditions={"capability_name": capability_name, "previously_approved": was_approved},
            effect="allow",
            confidence=0.8,
            training_data_size=1
        )


class DriftDetector:
    def __init__(self, learning_service: LearningService):
        self._service = learning_service
        self._baselines: dict[str, float] = {}

    def set_baseline(self, metric_name: str, value: float) -> None:
        self._baselines[metric_name] = value

    def detect_drift(
        self,
        metric_name: str,
        current_value: float,
        threshold_percent: float = 20.0,
    ) -> DriftDetection | None:
        baseline = self._baselines.get(metric_name)
        if baseline is None:
            self.set_baseline(metric_name, current_value)
            return None

        if baseline == 0:
            return None

        change_percent = abs((current_value - baseline) / baseline) * 100

        if change_percent < threshold_percent:
            return None

        severity = "low"
        if change_percent > 50:
            severity = "high"
        elif change_percent > 30:
            severity = "medium"

        drift = DriftDetection(
            drift_type=DriftType.CAPABILITY_USAGE,
            metric_name=metric_name,
            baseline_value=baseline,
            current_value=current_value,
            change_percent=change_percent,
            severity=severity
        )

        self._service.record_drift(drift)
        self.set_baseline(metric_name, current_value)

        return drift

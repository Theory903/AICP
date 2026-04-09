import math
from collections import Counter

from .learning import DriftDetection, DriftDetector, DriftType, LearningService, MinedSkill


class TfIdfSkillMiner:
    """
    Advanced SkillMiner using TF-IDF style analysis to discover unique capability patterns.
    Identifies 'skills' by finding sets of capabilities that frequently co-occur
    but are rare across the entire set of sessions.
    """

    def __init__(self, learning_service: LearningService):
        self.service = learning_service
        self.sessions: list[list[str]] = []

    def add_session(self, capability_names: list[str]):
        """Record a sequence of capability executions from a session."""
        if capability_names:
            self.sessions.append(capability_names)

    def mine_skills(self, min_support: int = 2) -> list[MinedSkill]:
        """
        Discover frequent itemsets (capability groups) that form a 'Skill'.
        Uses a simplified Apriori-style pattern mining.
        """
        if not self.sessions:
            return []

        # Count individual capability frequencies
        all_caps = [cap for session in self.sessions for cap in session]
        cap_counts = Counter(all_caps)

        # Find frequent pairs (simplification for v1.0.0)
        pair_counts = Counter()
        for session in self.sessions:
            unique_caps = sorted(set(session))
            for i in range(len(unique_caps)):
                for j in range(i + 1, len(unique_caps)):
                    pair_counts[(unique_caps[i], unique_caps[j])] += 1

        mined = []
        for (cap1, cap2), count in pair_counts.items():
            if count >= min_support:
                # Calculate confidence (lift-like metric)
                # How much more likely are they to appear together than apart?
                support_a = cap_counts[cap1] / len(self.sessions)
                support_b = cap_counts[cap2] / len(self.sessions)
                support_ab = count / len(self.sessions)

                lift = support_ab / (support_a * support_b) if (support_a * support_b) > 0 else 0

                if lift > 1.5:  # Significant correlation
                    mined.append(MinedSkill(
                        source_capabilities=[cap1, cap2],
                        source_workflows=[],
                        pattern_type="co_occurrence_pattern",
                        confidence=min(1.0, lift / 5.0),
                        suggested_name=f"{cap1.split('.')[-1]}-{cap2.split('.')[-1]} Skill",
                        suggested_description=f"Identified pattern between {cap1} and {cap2}"
                    ))

        for m in mined:
            self.service.add_mined_skill(m)

        return mined

class BayesianDriftDetector(DriftDetector):
    """
    Bayesian implementation of DriftDetector.
    Uses a moving average with standard deviation bounds to detect anomalous changes.
    """

    def __init__(self, learning_service: LearningService, window_size: int = 10):
        super().__init__(learning_service)
        self.window_size = window_size
        self.history: dict[str, list[float]] = {}

    def detect_drift(
        self,
        metric_name: str,
        current_value: float,
        threshold_percent: float = 2.0,
    ) -> DriftDetection | None:
        """
        Detect drift using Z-score (Standard Deviations from Mean).
        """
        if metric_name not in self.history:
            self.history[metric_name] = []

        hist = self.history[metric_name]
        hist.append(current_value)

        if len(hist) < self.window_size:
            return None

        # Maintain sliding window
        self.history[metric_name] = hist[-self.window_size:]
        window = self.history[metric_name][:-1] # Exclude current

        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return None

        z_score = abs(current_value - mean) / std_dev

        if z_score > threshold_percent:
            severity = "high" if z_score > threshold_percent * 2 else "medium"

            drift = DriftDetection(
                drift_type=DriftType.ERROR_RATES if "error" in metric_name.lower() else DriftType.CAPABILITY_USAGE,
                metric_name=metric_name,
                baseline_value=mean,
                current_value=current_value,
                change_percent=(abs(current_value - mean) / mean * 100) if mean != 0 else 0,
                severity=severity,
                recommendations=[f"Review {metric_name} for potential anomalies. Z-score: {z_score:.2f}"]
            )
            self._service.record_drift(drift)
            return drift

        return None

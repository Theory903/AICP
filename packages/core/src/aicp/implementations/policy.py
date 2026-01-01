"""Default policy engine implementation.

A simple in-memory policy engine that evaluates policies in order.
"""

from typing import Any

from aicp.interfaces.policy_engine import (
    Policy,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
)


class DefaultPolicyEngine(PolicyEngine):
    """In-memory policy engine with simple priority-based evaluation."""

    def __init__(self):
        self._policies: dict[str, Policy] = {}

    @property
    def engine_type(self) -> str:
        return "default"

    async def evaluate(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        context = context or {}
        sorted_policies = sorted(
            self._policies.values(),
            key=lambda p: p.priority,
            reverse=True,
        )

        for policy in sorted_policies:
            if self._matches(policy.subject, capability_name, context):
                if policy.condition:
                    if policy.condition.require_confirmation:
                        return PolicyDecision(
                            effect=PolicyEffect.ASK,
                            reason=f"Policy '{policy.name}' requires confirmation",
                            policy_name=policy.name,
                        )
                    if policy.condition.max_rate_per_minute:
                        return PolicyDecision(
                            effect=PolicyEffect.LIMIT,
                            reason=f"Rate limited by '{policy.name}'",
                            policy_name=policy.name,
                            metadata={"max_rate": policy.condition.max_rate_per_minute},
                        )

                if policy.effect == PolicyEffect.DENY:
                    return PolicyDecision(
                        effect=PolicyEffect.DENY,
                        reason=f"Denied by policy '{policy.name}': {policy.description}",
                        policy_name=policy.name,
                    )

        return PolicyDecision(
            effect=PolicyEffect.ALLOW,
            reason="No policies matched",
        )

    def _matches(
        self,
        subject: PolicySubject,
        capability_name: str,
        context: dict[str, Any],
    ) -> bool:
        if subject.capability_name and subject.capability_name != capability_name:
            return False
        if subject.capability_kind and context.get("kind") != subject.capability_kind:
            return False
        if subject.provider and context.get("provider") != subject.provider:
            if subject.provider not in context.get("providers", []):
                return False
        if subject.tags:
            context_tags = set(context.get("tags", []))
            if not context_tags.intersection(set(subject.tags)):
                return False
        return True

    async def add_policy(self, policy: Policy) -> None:
        self._policies[policy.name] = policy

    async def remove_policy(self, policy_name: str) -> bool:
        if policy_name in self._policies:
            del self._policies[policy_name]
            return True
        return False

    async def list_policies(self) -> list[Policy]:
        return list(self._policies.values())

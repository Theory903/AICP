"""Default policy engine implementation.

Provides:
- DefaultPolicyEngine: in-memory policy evaluation
- ConfigPolicyEngine: read-only policy evaluation from aicp.yaml
"""

from __future__ import annotations

import fnmatch
from typing import Any

from aicp.config import AicpProjectConfig
from aicp.interfaces.policy_engine import (
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicyError,
    PolicySubject,
)


class DefaultPolicyEngine(PolicyEngine):
    """In-memory policy engine with priority-based evaluation."""

    def __init__(self) -> None:
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
        """Evaluate registered policies in descending priority order."""
        safe_context = context or {}
        policies = sorted(
            self._policies.values(),
            key=lambda policy: (policy.priority, policy.name),
            reverse=True,
        )

        for policy in policies:
            if not self._matches(policy.subject, capability_name, safe_context):
                continue

            condition_decision = self._evaluate_condition(policy, arguments, safe_context)
            if condition_decision is not None:
                return condition_decision

            return PolicyDecision(
                effect=policy.effect,
                reason=self._build_reason(policy),
                policy_name=policy.name,
                metadata={
                    "matched_policy": policy.name,
                    "priority": policy.priority,
                    **policy.metadata,
                },
            )

        return PolicyDecision(
            effect=PolicyEffect.ALLOW,
            reason="No policies matched",
            metadata={"matched_policy": None},
        )

    def _matches(
        self,
        subject: PolicySubject,
        capability_name: str,
        context: dict[str, Any],
    ) -> bool:
        """Match a policy subject against a capability and its context."""
        if subject.capability_name and not fnmatch.fnmatch(capability_name, subject.capability_name):
            return False

        if subject.capability_kind:
            context_kind = context.get("kind")
            if context_kind != subject.capability_kind:
                return False

        if subject.provider:
            context_provider = context.get("provider")
            context_providers = context.get("providers", [])
            if context_provider != subject.provider and subject.provider not in context_providers:
                return False

        if subject.tags:
            context_tags = {str(tag) for tag in context.get("tags", [])}
            if not context_tags.intersection(subject.tags):
                return False

        return True

    def _evaluate_condition(
        self,
        policy: Policy,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> PolicyDecision | None:
        """Evaluate policy conditions and return an overriding decision if needed."""
        condition = policy.condition
        if condition is None:
            return None

        if condition.require_confirmation:
            return PolicyDecision(
                effect=PolicyEffect.ASK,
                reason=f"Policy '{policy.name}' requires confirmation",
                policy_name=policy.name,
                metadata={
                    "matched_policy": policy.name,
                    "require_confirmation": True,
                    **policy.metadata,
                },
            )

        if condition.max_rate_per_minute is not None:
            return PolicyDecision(
                effect=PolicyEffect.LIMIT,
                reason=f"Rate limited by policy '{policy.name}'",
                policy_name=policy.name,
                metadata={
                    "matched_policy": policy.name,
                    "max_rate_per_minute": condition.max_rate_per_minute,
                    **policy.metadata,
                },
            )

        if condition.max_amount is not None:
            amount = self._extract_amount(arguments)
            if amount is not None and amount > condition.max_amount:
                return PolicyDecision(
                    effect=PolicyEffect.DENY,
                    reason=(
                        f"Policy '{policy.name}' denied execution: "
                        f"amount {amount} exceeds limit {condition.max_amount}"
                    ),
                    policy_name=policy.name,
                    metadata={
                        "matched_policy": policy.name,
                        "max_amount": condition.max_amount,
                        "requested_amount": amount,
                        **policy.metadata,
                    },
                )

        return None

    @staticmethod
    def _extract_amount(arguments: dict[str, Any]) -> float | None:
        """Extract a numeric amount-like value from arguments if present."""
        amount_keys = ("amount", "value", "price", "total", "cost")
        for key in amount_keys:
            if key in arguments:
                try:
                    return float(arguments[key])
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _build_reason(policy: Policy) -> str:
        """Build a human-readable reason for a matched policy."""
        if policy.description:
            return f"Matched policy '{policy.name}': {policy.description}"
        return f"Matched policy '{policy.name}'"

    async def add_policy(self, policy: Policy) -> None:
        self._policies[policy.name] = policy

    async def remove_policy(self, policy_name: str) -> bool:
        if policy_name in self._policies:
            del self._policies[policy_name]
            return True
        return False

    async def list_policies(self) -> list[Policy]:
        return sorted(
            self._policies.values(),
            key=lambda policy: (policy.priority, policy.name),
            reverse=True,
        )


class ConfigPolicyEngine(PolicyEngine):
    """Policy engine that evaluates declarative rules from aicp.yaml."""

    def __init__(self, config: AicpProjectConfig):
        self._config = config

    @property
    def engine_type(self) -> str:
        return "config"

    async def evaluate(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        safe_context = context or {}
        kind = str(safe_context.get("kind", "action"))
        is_destructive = bool(safe_context.get("is_destructive", False))

        configured_effect = self._config.effective_effect(
            capability_name=capability_name,
            kind=kind,
            is_destructive=is_destructive,
        )
        matched_rule = self._config.find_rule(capability_name)

        effect = self._map_effect(configured_effect)
        reason = self._build_reason(
            effect=effect,
            configured_effect=configured_effect,
            rule=matched_rule,
            kind=kind,
            is_destructive=is_destructive,
        )

        metadata: dict[str, Any] = {
            "matched_rule": matched_rule.match if matched_rule else None,
            "configured_effect": configured_effect,
            "kind": kind,
            "is_destructive": is_destructive,
        }

        if matched_rule and matched_rule.rpm is not None:
            metadata["rpm"] = matched_rule.rpm

        return PolicyDecision(
            effect=effect,
            reason=reason,
            policy_name=f"config:{matched_rule.match}" if matched_rule else None,
            metadata=metadata,
        )

    @staticmethod
    def _map_effect(effect_str: str) -> PolicyEffect:
        """Map config effect strings into protocol policy effects."""
        if effect_str == "require_approval":
            return PolicyEffect.ASK
        try:
            return PolicyEffect(effect_str)
        except ValueError as exc:
            raise PolicyError(
                f"Unsupported configured policy effect: {effect_str}",
                effect=None,
                details={"configured_effect": effect_str},
            ) from exc

    @staticmethod
    def _build_reason(
        *,
        effect: PolicyEffect,
        configured_effect: str,
        rule: Any,
        kind: str,
        is_destructive: bool,
    ) -> str:
        """Build a human-readable reason for the config decision."""
        if rule:
            if getattr(rule, "reason", None):
                return str(rule.reason)
            return f"Matched config rule '{rule.match}' with effect '{configured_effect}'"

        if effect == PolicyEffect.DENY:
            if is_destructive:
                return "Denied by default destructive policy"
            return f"Denied by default policy for kind '{kind}'"

        if effect == PolicyEffect.LIMIT:
            return f"Limited by default policy for kind '{kind}'"

        if effect == PolicyEffect.ASK:
            if is_destructive:
                return "Approval required by default destructive policy"
            return f"Confirmation required by default policy for kind '{kind}'"

        return "Allowed by default policy"

    async def add_policy(self, policy: Policy) -> None:
        raise RuntimeError("ConfigPolicyEngine is read-only. Edit aicp.yaml instead.")

    async def remove_policy(self, policy_name: str) -> bool:
        raise RuntimeError("ConfigPolicyEngine is read-only. Edit aicp.yaml instead.")

    async def list_policies(self) -> list[Policy]:
        """Expose config rules as read-only Policy objects for introspection."""
        policies: list[Policy] = []

        for index, rule in enumerate(self._config.rules):
            effect = self._map_effect(rule.effect)

            condition: PolicyCondition | None = None
            if rule.rpm is not None:
                condition = PolicyCondition(max_rate_per_minute=rule.rpm)
            elif effect == PolicyEffect.ASK:
                condition = PolicyCondition(require_confirmation=True)

            policies.append(
                Policy(
                    name=f"config:{rule.match}",
                    description=rule.reason or f"Config rule for {rule.match}",
                    effect=effect,
                    subject=PolicySubject(capability_name=rule.match),
                    condition=condition,
                    priority=len(self._config.rules) - index,
                    metadata={
                        "source": "aicp.yaml",
                        "configured_effect": rule.effect,
                        "match": rule.match,
                        "rpm": rule.rpm,
                    },
                )
            )

        return policies
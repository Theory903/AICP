"""Policy engine interface.

Defines the contract for evaluating policies on capability execution.
Policies define what is allowed, restricted, or requires confirmation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PolicyEffect(str, Enum):
    """The effect of a policy decision."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # Requires user confirmation or approval
    LIMIT = "limit"  # Allowed with limits such as rate or amount


class PolicySubject(BaseModel):
    """What the policy applies to."""

    model_config = ConfigDict(extra="forbid")

    capability_name: str | None = None
    capability_kind: str | None = None
    provider: str | None = None
    tags: list[str] = Field(default_factory=list)


class PolicyCondition(BaseModel):
    """Conditions under which the policy applies."""

    model_config = ConfigDict(extra="forbid")

    max_rate_per_minute: int | None = Field(default=None, ge=1)
    max_amount: float | None = Field(default=None, ge=0)
    require_confirmation: bool = False
    allowed_times: str | None = None  # e.g. "09:00-17:00"
    ip_whitelist: list[str] | None = None


class Policy(BaseModel):
    """A policy rule."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    effect: PolicyEffect
    subject: PolicySubject
    condition: PolicyCondition | None = None
    priority: int = 0  # Higher = evaluated first
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """The result of policy evaluation."""

    model_config = ConfigDict(extra="forbid")

    effect: PolicyEffect
    reason: str
    policy_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_allowed(self) -> bool:
        """Return True when execution may proceed immediately."""
        return self.effect == PolicyEffect.ALLOW

    @property
    def requires_confirmation(self) -> bool:
        """Return True when user confirmation or approval is required."""
        return self.effect == PolicyEffect.ASK

    @property
    def is_denied(self) -> bool:
        """Return True when execution is denied."""
        return self.effect == PolicyEffect.DENY

    @property
    def is_limited(self) -> bool:
        """Return True when execution is subject to limits."""
        return self.effect == PolicyEffect.LIMIT


class PolicyError(Exception):
    """Raised when policy evaluation fails."""

    def __init__(
        self,
        message: str,
        policy_name: str | None = None,
        effect: PolicyEffect | None = None,
        details: Any = None,
    ):
        self.policy_name = policy_name
        self.effect = effect
        self.details = details
        super().__init__(message)


class PolicyEngine(ABC):
    """Abstract interface for policy evaluation.

    Policy engines evaluate incoming capability execution requests
    against a set of policy rules and return a decision.
    """

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Type identifier for this policy engine."""
        raise NotImplementedError

    @abstractmethod
    async def evaluate(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluate policies for a capability execution request.

        Args:
            capability_name: Name of the capability being executed.
            arguments: Arguments being passed to the capability.
            context: Optional execution context such as user or session metadata.

        Returns:
            PolicyDecision indicating whether to allow, deny, ask, or limit.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_policy(self, policy: Policy) -> None:
        """Add a policy to the engine."""
        raise NotImplementedError

    @abstractmethod
    async def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name.

        Returns:
            True if removed, False if not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_policies(self) -> list[Policy]:
        """List all policies in the engine."""
        raise NotImplementedError

    async def must_authorize(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Assert that execution is immediately authorized.

        Raises PolicyError when execution is denied, requires confirmation,
        or is subject to limiting that the caller has not explicitly handled.
        """
        decision = await self.evaluate(capability_name, arguments, context)

        if decision.effect == PolicyEffect.DENY:
            raise PolicyError(
                message=f"Policy denied: {decision.reason}",
                policy_name=decision.policy_name,
                effect=decision.effect,
                details=decision.metadata,
            )

        if decision.effect == PolicyEffect.ASK:
            raise PolicyError(
                message=f"Policy requires confirmation: {decision.reason}",
                policy_name=decision.policy_name,
                effect=decision.effect,
                details=decision.metadata,
            )

        if decision.effect == PolicyEffect.LIMIT:
            raise PolicyError(
                message=f"Policy requires limit handling: {decision.reason}",
                policy_name=decision.policy_name,
                effect=decision.effect,
                details=decision.metadata,
            )
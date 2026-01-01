"""Policy engine interface.

Defines the contract for evaluating policies on capability execution.
Policies define what is allowed, restricted, or requires confirmation.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PolicyEffect(str, Enum):
    """The effect of a policy decision."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # Requires user confirmation
    LIMIT = "limit"  # Allowed with limits (rate, amount, etc.)


class PolicySubject(BaseModel):
    """What the policy applies to."""

    capability_name: str | None = None
    capability_kind: str | None = None
    provider: str | None = None
    tags: list[str] = []


class PolicyCondition(BaseModel):
    """Conditions under which the policy applies."""

    max_rate_per_minute: int | None = None
    max_amount: float | None = None
    require_confirmation: bool = False
    allowed_times: str | None = None  # e.g., "09:00-17:00"
    ip_whitelist: list[str] | None = None


class Policy(BaseModel):
    """A policy rule."""

    name: str
    description: str = ""
    effect: PolicyEffect
    subject: PolicySubject
    condition: PolicyCondition | None = None
    priority: int = 0  # Higher = evaluated first
    metadata: dict[str, Any] = {}


class PolicyDecision(BaseModel):
    """The result of policy evaluation."""

    effect: PolicyEffect
    reason: str
    policy_name: str | None = None
    metadata: dict[str, Any] = {}


class PolicyError(Exception):
    """Raised when policy evaluation fails."""

    pass


class PolicyEngine(ABC):
    """Abstract interface for policy evaluation.

    Policy engines evaluate incoming capability execution requests
    against a set of policy rules and return a decision.
    """

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Type identifier for this policy engine."""
        pass

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
            context: Optional execution context (user, session, etc.).

        Returns:
            PolicyDecision indicating whether to allow, deny, or ask.
        """
        pass

    @abstractmethod
    async def add_policy(self, policy: Policy) -> None:
        """Add a policy to the engine.

        Args:
            policy: The policy to add.
        """
        pass

    @abstractmethod
    async def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name.

        Args:
            policy_name: Name of the policy to remove.

        Returns:
            True if removed, False if not found.
        """
        pass

    @abstractmethod
    async def list_policies(self) -> list[Policy]:
        """List all policies in the engine.

        Returns:
            List of all policies.
        """
        pass

    async def must_authorize(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Assert that execution is authorized.

        Raises PolicyError if not allowed.

        Args:
            capability_name: Name of the capability.
            arguments: Arguments for the capability.
            context: Execution context.

        Raises:
            PolicyError: If execution is not allowed.
        """
        decision = await self.evaluate(capability_name, arguments, context)
        if decision.effect == PolicyEffect.DENY:
            raise PolicyError(f"Policy denied: {decision.reason}")
        if decision.effect == PolicyEffect.ASK:
            raise PolicyError(f"Policy requires confirmation: {decision.reason}")

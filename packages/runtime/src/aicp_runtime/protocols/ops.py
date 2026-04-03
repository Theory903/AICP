"""Ops Cognitive Protocol for AICP.

Governs how the agent executes and manages infrastructure and system
operations.  Every ops action the agent initiates goes through this protocol
so that:
  - Operations are structured and auditable.
  - Required fields are enforced per operation type.
  - Risk level is classified consistently.
  - The agent tracks ops actions per session.

Operations:
  DEPLOY        — deploy an artifact to a target service
  SCALE         — change the replica count of a service
  RESTART       — restart a service
  ROLLBACK      — roll back a service to a previous version
  HEALTH_CHECK  — check the health of a service (read-only, low risk)
  CONFIG_UPDATE — push a configuration change to a service
  LOG_QUERY     — query logs for a service (read-only, low risk)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class OpsProtocolError(Exception):
    """Raised when an Ops protocol constraint is violated."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OpsOperationType(str, Enum):
    DEPLOY = "deploy"
    SCALE = "scale"
    RESTART = "restart"
    ROLLBACK = "rollback"
    HEALTH_CHECK = "health_check"
    CONFIG_UPDATE = "config_update"
    LOG_QUERY = "log_query"


class OpsRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Default risk levels per operation type (can be overridden).
_DEFAULT_RISK: dict[OpsOperationType, OpsRiskLevel] = {
    OpsOperationType.DEPLOY: OpsRiskLevel.MEDIUM,
    OpsOperationType.SCALE: OpsRiskLevel.MEDIUM,
    OpsOperationType.RESTART: OpsRiskLevel.MEDIUM,
    OpsOperationType.ROLLBACK: OpsRiskLevel.HIGH,
    OpsOperationType.HEALTH_CHECK: OpsRiskLevel.LOW,
    OpsOperationType.CONFIG_UPDATE: OpsRiskLevel.MEDIUM,
    OpsOperationType.LOG_QUERY: OpsRiskLevel.LOW,
}


# ---------------------------------------------------------------------------
# OpsAction
# ---------------------------------------------------------------------------


@dataclass
class OpsAction:
    """A structured operation on a system/infrastructure resource."""

    operation: OpsOperationType
    target: str
    artifact: Optional[str] = None
    replicas: Optional[int] = None
    rollback_version: Optional[str] = None
    query: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    risk_level: OpsRiskLevel = field(default=OpsRiskLevel.MEDIUM)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "target": self.target,
            "artifact": self.artifact,
            "replicas": self.replicas,
            "rollback_version": self.rollback_version,
            "query": self.query,
            "config": self.config,
            "risk_level": self.risk_level.value,
        }


# ---------------------------------------------------------------------------
# OpsProtocol
# ---------------------------------------------------------------------------


class OpsProtocol:
    """Manages structured infrastructure/ops actions for a session."""

    def __init__(self) -> None:
        self._history: list[OpsAction] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[OpsAction]:
        return list(self._history)

    @property
    def high_risk_count(self) -> int:
        return sum(1 for a in self._history if a.risk_level == OpsRiskLevel.HIGH)

    # ------------------------------------------------------------------
    # Action builders
    # ------------------------------------------------------------------

    def deploy(self, target: str, artifact: Optional[str]) -> OpsAction:
        """Create a DEPLOY action (requires artifact)."""
        self._validate_target(target)
        if not artifact:
            raise OpsProtocolError("artifact is required for DEPLOY operations")
        action = OpsAction(
            operation=OpsOperationType.DEPLOY,
            target=target,
            artifact=artifact,
            risk_level=_DEFAULT_RISK[OpsOperationType.DEPLOY],
        )
        self._record(action)
        return action

    def scale(self, target: str, replicas: int) -> OpsAction:
        """Create a SCALE action (requires replicas >= 1)."""
        self._validate_target(target)
        if replicas is None or replicas < 1:
            raise OpsProtocolError(
                f"replicas must be a positive integer, got: {replicas}"
            )
        action = OpsAction(
            operation=OpsOperationType.SCALE,
            target=target,
            replicas=replicas,
            risk_level=_DEFAULT_RISK[OpsOperationType.SCALE],
        )
        self._record(action)
        return action

    def restart(self, target: str) -> OpsAction:
        """Create a RESTART action."""
        self._validate_target(target)
        action = OpsAction(
            operation=OpsOperationType.RESTART,
            target=target,
            risk_level=_DEFAULT_RISK[OpsOperationType.RESTART],
        )
        self._record(action)
        return action

    def rollback(self, target: str, version: Optional[str]) -> OpsAction:
        """Create a ROLLBACK action (requires version)."""
        self._validate_target(target)
        if not version:
            raise OpsProtocolError("version is required for ROLLBACK operations")
        action = OpsAction(
            operation=OpsOperationType.ROLLBACK,
            target=target,
            rollback_version=version,
            risk_level=_DEFAULT_RISK[OpsOperationType.ROLLBACK],
        )
        self._record(action)
        return action

    def health_check(self, target: str) -> OpsAction:
        """Create a HEALTH_CHECK action (read-only, low risk)."""
        self._validate_target(target)
        action = OpsAction(
            operation=OpsOperationType.HEALTH_CHECK,
            target=target,
            risk_level=_DEFAULT_RISK[OpsOperationType.HEALTH_CHECK],
        )
        self._record(action)
        return action

    def log_query(self, target: str, query: Optional[str]) -> OpsAction:
        """Create a LOG_QUERY action (requires query string)."""
        self._validate_target(target)
        if not query:
            raise OpsProtocolError("query is required for LOG_QUERY operations")
        action = OpsAction(
            operation=OpsOperationType.LOG_QUERY,
            target=target,
            query=query,
            risk_level=_DEFAULT_RISK[OpsOperationType.LOG_QUERY],
        )
        self._record(action)
        return action

    def config_update(
        self, target: str, config: Optional[dict[str, Any]]
    ) -> OpsAction:
        """Create a CONFIG_UPDATE action (requires config dict)."""
        self._validate_target(target)
        if config is None:
            raise OpsProtocolError("config is required for CONFIG_UPDATE operations")
        action = OpsAction(
            operation=OpsOperationType.CONFIG_UPDATE,
            target=target,
            config=dict(config),
            risk_level=_DEFAULT_RISK[OpsOperationType.CONFIG_UPDATE],
        )
        self._record(action)
        return action

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_target(self, target: str) -> None:
        if not target or not target.strip():
            raise OpsProtocolError("target must not be empty")

    def _record(self, action: OpsAction) -> None:
        self._history.append(action)

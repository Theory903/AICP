"""Tests for the Ops Cognitive Protocol (TDD).

The Ops (Operations) Protocol governs how the agent executes and manages
infrastructure/system operations:
  - Produces an OpsAction (a structured operation on system resources)
  - Classifies operation type: DEPLOY, SCALE, RESTART, ROLLBACK, HEALTH_CHECK,
    CONFIG_UPDATE, LOG_QUERY
  - Enforces required fields per operation type
  - Validates target (non-empty, no traversal-style injection)
  - Tracks ops actions per session
  - Risk classification: low / medium / high
"""

from __future__ import annotations

import pytest

from aicp_runtime.protocols.ops import (
    OpsProtocol,
    OpsAction,
    OpsOperationType,
    OpsRiskLevel,
    OpsProtocolError,
)


# ---------------------------------------------------------------------------
# OpsAction
# ---------------------------------------------------------------------------


class TestOpsAction:
    def test_deploy_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.DEPLOY,
            target="service/api",
            artifact="api:v2.1.0",
        )
        assert action.operation == OpsOperationType.DEPLOY
        assert action.target == "service/api"
        assert action.artifact == "api:v2.1.0"

    def test_scale_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.SCALE,
            target="service/worker",
            replicas=5,
        )
        assert action.replicas == 5

    def test_rollback_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.ROLLBACK,
            target="service/api",
            rollback_version="api:v2.0.9",
        )
        assert action.rollback_version == "api:v2.0.9"

    def test_health_check_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.HEALTH_CHECK,
            target="service/api",
        )
        assert action.operation == OpsOperationType.HEALTH_CHECK

    def test_log_query_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.LOG_QUERY,
            target="service/api",
            query="level=error last=1h",
        )
        assert action.query == "level=error last=1h"

    def test_config_update_action_fields(self):
        action = OpsAction(
            operation=OpsOperationType.CONFIG_UPDATE,
            target="service/api",
            config={"timeout": 30},
        )
        assert action.config == {"timeout": 30}

    def test_risk_level_defaults_to_medium(self):
        action = OpsAction(
            operation=OpsOperationType.RESTART,
            target="service/api",
        )
        assert action.risk_level == OpsRiskLevel.MEDIUM

    def test_risk_level_can_be_set(self):
        action = OpsAction(
            operation=OpsOperationType.ROLLBACK,
            target="service/api",
            rollback_version="api:v1.0.0",
            risk_level=OpsRiskLevel.HIGH,
        )
        assert action.risk_level == OpsRiskLevel.HIGH

    def test_to_dict_includes_all_fields(self):
        action = OpsAction(
            operation=OpsOperationType.DEPLOY,
            target="service/api",
            artifact="api:v2.1.0",
            risk_level=OpsRiskLevel.MEDIUM,
        )
        d = action.to_dict()
        assert d["operation"] == "deploy"
        assert d["target"] == "service/api"
        assert d["artifact"] == "api:v2.1.0"
        assert d["risk_level"] == "medium"


# ---------------------------------------------------------------------------
# OpsProtocol
# ---------------------------------------------------------------------------


class TestOpsProtocol:
    # ------------------------------------------------------------------
    # Action builders — happy path
    # ------------------------------------------------------------------

    def test_deploy_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.deploy("service/api", artifact="api:v2.1.0")
        assert isinstance(action, OpsAction)
        assert action.operation == OpsOperationType.DEPLOY

    def test_scale_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.scale("service/worker", replicas=3)
        assert action.operation == OpsOperationType.SCALE
        assert action.replicas == 3

    def test_restart_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.restart("service/api")
        assert action.operation == OpsOperationType.RESTART

    def test_rollback_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.rollback("service/api", version="api:v1.9.0")
        assert action.operation == OpsOperationType.ROLLBACK
        assert action.rollback_version == "api:v1.9.0"

    def test_health_check_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.health_check("service/api")
        assert action.operation == OpsOperationType.HEALTH_CHECK

    def test_log_query_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.log_query("service/api", query="level=error last=30m")
        assert action.operation == OpsOperationType.LOG_QUERY
        assert action.query == "level=error last=30m"

    def test_config_update_returns_ops_action(self):
        ops = OpsProtocol()
        action = ops.config_update("service/api", config={"debug": False})
        assert action.operation == OpsOperationType.CONFIG_UPDATE
        assert action.config == {"debug": False}

    # ------------------------------------------------------------------
    # Validation — required fields
    # ------------------------------------------------------------------

    def test_deploy_requires_artifact(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="artifact"):
            ops.deploy("service/api", artifact=None)  # type: ignore[arg-type]

    def test_scale_requires_positive_replicas(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="replicas"):
            ops.scale("service/worker", replicas=0)

    def test_scale_requires_non_negative_replicas(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="replicas"):
            ops.scale("service/worker", replicas=-1)

    def test_rollback_requires_version(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="version"):
            ops.rollback("service/api", version=None)  # type: ignore[arg-type]

    def test_log_query_requires_query_string(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="query"):
            ops.log_query("service/api", query=None)  # type: ignore[arg-type]

    def test_config_update_requires_config_dict(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="config"):
            ops.config_update("service/api", config=None)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Target validation
    # ------------------------------------------------------------------

    def test_empty_target_is_rejected(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="target"):
            ops.restart("")

    def test_whitespace_target_is_rejected(self):
        ops = OpsProtocol()
        with pytest.raises(OpsProtocolError, match="target"):
            ops.restart("   ")

    # ------------------------------------------------------------------
    # Risk level helpers
    # ------------------------------------------------------------------

    def test_deploy_default_risk_is_medium(self):
        ops = OpsProtocol()
        action = ops.deploy("service/api", artifact="api:v3.0.0")
        assert action.risk_level == OpsRiskLevel.MEDIUM

    def test_rollback_default_risk_is_high(self):
        ops = OpsProtocol()
        action = ops.rollback("service/api", version="api:v1.0.0")
        assert action.risk_level == OpsRiskLevel.HIGH

    def test_health_check_default_risk_is_low(self):
        ops = OpsProtocol()
        action = ops.health_check("service/api")
        assert action.risk_level == OpsRiskLevel.LOW

    def test_log_query_default_risk_is_low(self):
        ops = OpsProtocol()
        action = ops.log_query("service/api", query="level=error")
        assert action.risk_level == OpsRiskLevel.LOW

    def test_restart_default_risk_is_medium(self):
        ops = OpsProtocol()
        action = ops.restart("service/api")
        assert action.risk_level == OpsRiskLevel.MEDIUM

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def test_history_tracks_all_actions(self):
        ops = OpsProtocol()
        ops.health_check("service/api")
        ops.restart("service/api")
        ops.deploy("service/api", artifact="api:v2.0.0")
        assert len(ops.history) == 3

    def test_history_is_ordered(self):
        ops = OpsProtocol()
        ops.health_check("service/api")
        ops.restart("service/api")
        assert ops.history[0].operation == OpsOperationType.HEALTH_CHECK
        assert ops.history[1].operation == OpsOperationType.RESTART

    def test_clear_history(self):
        ops = OpsProtocol()
        ops.health_check("service/api")
        ops.clear_history()
        assert ops.history == []

    def test_high_risk_action_count(self):
        ops = OpsProtocol()
        ops.rollback("service/api", version="api:v1.0.0")
        ops.rollback("service/db", version="db:v0.9.0")
        ops.health_check("service/api")
        assert ops.high_risk_count == 2

    def test_history_is_a_copy(self):
        ops = OpsProtocol()
        ops.health_check("service/api")
        history = ops.history
        history.clear()
        assert len(ops.history) == 1

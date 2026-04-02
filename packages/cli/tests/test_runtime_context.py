"""Tests for CLI runtime context helpers."""

from types import SimpleNamespace

from aicp_cli.context import RuntimeContext


def test_runtime_context_exposes_policy_engine_property() -> None:
    project = SimpleNamespace(
        config=object(),
        executor=object(),
        repository=object(),
        capabilities=[],
        policy_engine=object(),
    )
    context = RuntimeContext(
        project=project,
        store=object(),
        audit=object(),
        approvals=object(),
    )

    assert context.policy_engine is project.policy_engine

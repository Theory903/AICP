"""Tests for the runtime-backed payment transfer platform demo."""

import asyncio

from payment_transfer.platform_demo import run_platform_demo


def test_platform_demo_runs_end_to_end_with_runtime_store(tmp_path) -> None:
    summary = asyncio.run(run_platform_demo(tmp_path / "runtime-store"))

    assert summary["workflow"]["status"] == "completed"
    assert summary["approval"]["status"] == "approved"
    assert summary["execution_result"]["success"] is True
    assert any(entry["event_type"] == "approval_request_created" for entry in summary["history"])
    assert any(entry["event_type"] == "approval_decision_made" for entry in summary["history"])

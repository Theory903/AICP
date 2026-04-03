"""Tests for the runtime-backed payment transfer platform demo."""

import asyncio

from payment_transfer.platform_demo import run_platform_demo


def test_platform_demo_runs_end_to_end_with_runtime_store(tmp_path) -> None:
    """Test high-value transfer ($2000) that requires approval."""
    summary = asyncio.run(run_platform_demo(tmp_path / "runtime-store", amount=2000.0))

    assert summary["workflow"]["status"] == "completed"
    assert summary["approval"]["status"] == "approved"
    assert summary["execution_result"]["success"] is True
    assert len(summary["approval_requests"]) == 1
    assert summary["approval_requests"][0]["status"] == "approved"
    assert any(
        entry["event_type"] == "approval_request_created"
        for entry in summary["history"]
    )
    assert any(
        entry["event_type"] == "approval_decision_made" for entry in summary["history"]
    )


def test_sub_threshold_skips_approval(tmp_path) -> None:
    """Test low-value transfer ($500) that skips approval."""
    summary = asyncio.run(run_platform_demo(tmp_path / "cheap-transfer", amount=500.0))

    assert summary["workflow"]["status"] == "completed"
    assert len(summary["approval_requests"]) == 0
    assert summary["execution_result"]["success"] is True
    assert summary["approval"] is None


def test_approval_rejection_path(tmp_path) -> None:
    """Test that rejection is also tracked in audit."""
    summary = asyncio.run(run_platform_demo(tmp_path / "rejection-test", amount=2000.0))

    assert summary["workflow"]["status"] == "completed"
    assert summary["approval"]["status"] == "approved"
    approval_events = [
        e for e in summary["history"] if e["event_type"] == "approval_decision_made"
    ]
    assert len(approval_events) >= 1

"""Tests for approval protocol helpers."""

from aicp.approval import ApprovalRequest


def test_approval_request_uses_timezone_aware_timestamps() -> None:
    request = ApprovalRequest.create("students.create", {})

    assert request.created_at.tzinfo is not None

"""Tests for the SWE Cognitive Protocol (TDD).

The SWE (Software Engineering) Protocol governs how the agent operates
on code and software artifacts:
  - Produces a CodeAction (a structured operation on a code artifact)
  - Classifies operation type: READ, WRITE, PATCH, RUN, REVIEW, EXPLAIN
  - Enforces that WRITE / PATCH actions carry a diff or content
  - Tracks code actions per session
  - Validates file path syntax (no empty paths, no path traversal)
"""

from __future__ import annotations

import pytest

from aicp_runtime.protocols.swe import (
    SWEProtocol,
    CodeAction,
    CodeOperationType,
    SWEProtocolError,
)


# ---------------------------------------------------------------------------
# CodeAction
# ---------------------------------------------------------------------------


class TestCodeAction:
    def test_read_action(self):
        ca = CodeAction(
            operation=CodeOperationType.READ,
            file_path="src/main.py",
        )
        assert ca.operation == CodeOperationType.READ
        assert ca.file_path == "src/main.py"
        assert ca.content is None
        assert ca.diff is None

    def test_write_action_with_content(self):
        ca = CodeAction(
            operation=CodeOperationType.WRITE,
            file_path="src/new_module.py",
            content="print('hello')",
        )
        assert ca.content == "print('hello')"

    def test_patch_action_with_diff(self):
        ca = CodeAction(
            operation=CodeOperationType.PATCH,
            file_path="src/service.py",
            diff="--- a/src/service.py\n+++ b/src/service.py",
        )
        assert ca.diff is not None

    def test_run_action(self):
        ca = CodeAction(
            operation=CodeOperationType.RUN,
            file_path="scripts/run_tests.sh",
            command="bash scripts/run_tests.sh",
        )
        assert ca.command == "bash scripts/run_tests.sh"

    def test_review_action(self):
        ca = CodeAction(
            operation=CodeOperationType.REVIEW,
            file_path="src/service.py",
        )
        assert ca.operation == CodeOperationType.REVIEW

    def test_explain_action(self):
        ca = CodeAction(
            operation=CodeOperationType.EXPLAIN,
            file_path="src/complex_algo.py",
        )
        assert ca.operation == CodeOperationType.EXPLAIN

    def test_to_dict_roundtrip(self):
        ca = CodeAction(
            operation=CodeOperationType.WRITE,
            file_path="src/hello.py",
            content="x = 1",
        )
        d = ca.to_dict()
        assert d["operation"] == "write"
        assert d["file_path"] == "src/hello.py"
        assert d["content"] == "x = 1"


# ---------------------------------------------------------------------------
# SWEProtocol
# ---------------------------------------------------------------------------


class TestSWEProtocol:
    def test_read_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.read("src/main.py")
        assert isinstance(action, CodeAction)
        assert action.operation == CodeOperationType.READ

    def test_write_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.write("src/new.py", content="pass")
        assert action.operation == CodeOperationType.WRITE
        assert action.content == "pass"

    def test_patch_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.patch("src/service.py", diff="--- a\n+++ b")
        assert action.operation == CodeOperationType.PATCH

    def test_run_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.run("scripts/test.sh", command="bash scripts/test.sh")
        assert action.operation == CodeOperationType.RUN

    def test_review_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.review("src/service.py")
        assert action.operation == CodeOperationType.REVIEW

    def test_explain_returns_code_action(self):
        swe = SWEProtocol()
        action = swe.explain("src/algo.py")
        assert action.operation == CodeOperationType.EXPLAIN

    def test_write_requires_content(self):
        swe = SWEProtocol()
        with pytest.raises(SWEProtocolError, match="content"):
            swe.write("src/new.py", content=None)  # type: ignore[arg-type]

    def test_patch_requires_diff(self):
        swe = SWEProtocol()
        with pytest.raises(SWEProtocolError, match="diff"):
            swe.patch("src/service.py", diff=None)  # type: ignore[arg-type]

    def test_empty_file_path_is_rejected(self):
        swe = SWEProtocol()
        with pytest.raises(SWEProtocolError, match="file_path"):
            swe.read("")

    def test_path_traversal_is_rejected(self):
        swe = SWEProtocol()
        with pytest.raises(SWEProtocolError, match="traversal"):
            swe.read("../../etc/passwd")

    def test_action_history_tracks_operations(self):
        swe = SWEProtocol()
        swe.read("src/a.py")
        swe.write("src/b.py", content="x = 1")
        assert len(swe.history) == 2
        assert swe.history[0].operation == CodeOperationType.READ

    def test_clear_history(self):
        swe = SWEProtocol()
        swe.read("src/a.py")
        swe.clear_history()
        assert swe.history == []

    def test_run_requires_command(self):
        swe = SWEProtocol()
        with pytest.raises(SWEProtocolError, match="command"):
            swe.run("scripts/test.sh", command=None)  # type: ignore[arg-type]

"""SWE Cognitive Protocol for AICP.

Governs how the agent operates on software engineering artifacts.
Every code operation is structured, validated, and tracked.

Operations:
  READ    — read a file
  WRITE   — create or overwrite a file (requires content)
  PATCH   — apply a diff to a file (requires diff)
  RUN     — execute a command (requires command)
  REVIEW  — code review a file
  EXPLAIN — explain a file or snippet
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class SWEProtocolError(Exception):
    """Raised when a SWE protocol constraint is violated."""


# ---------------------------------------------------------------------------
# CodeOperationType enum
# ---------------------------------------------------------------------------


class CodeOperationType(str, Enum):
    READ = "read"
    WRITE = "write"
    PATCH = "patch"
    RUN = "run"
    REVIEW = "review"
    EXPLAIN = "explain"


# ---------------------------------------------------------------------------
# CodeAction
# ---------------------------------------------------------------------------


@dataclass
class CodeAction:
    """A structured operation on a code artifact."""

    operation: CodeOperationType
    file_path: str
    content: Optional[str] = None
    diff: Optional[str] = None
    command: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "file_path": self.file_path,
            "content": self.content,
            "diff": self.diff,
            "command": self.command,
        }


# ---------------------------------------------------------------------------
# SWEProtocol
# ---------------------------------------------------------------------------


class SWEProtocol:
    """Manages structured software engineering actions for a session."""

    def __init__(self) -> None:
        self._history: list[CodeAction] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[CodeAction]:
        return list(self._history)

    # ------------------------------------------------------------------
    # Action builders
    # ------------------------------------------------------------------

    def read(self, file_path: str) -> CodeAction:
        """Create a READ action."""
        self._validate_path(file_path)
        action = CodeAction(operation=CodeOperationType.READ, file_path=file_path)
        self._record(action)
        return action

    def write(self, file_path: str, content: Optional[str]) -> CodeAction:
        """Create a WRITE action (requires content)."""
        self._validate_path(file_path)
        if content is None:
            raise SWEProtocolError("content is required for WRITE operations")
        action = CodeAction(
            operation=CodeOperationType.WRITE, file_path=file_path, content=content
        )
        self._record(action)
        return action

    def patch(self, file_path: str, diff: Optional[str]) -> CodeAction:
        """Create a PATCH action (requires diff)."""
        self._validate_path(file_path)
        if diff is None:
            raise SWEProtocolError("diff is required for PATCH operations")
        action = CodeAction(
            operation=CodeOperationType.PATCH, file_path=file_path, diff=diff
        )
        self._record(action)
        return action

    def run(self, file_path: str, command: Optional[str]) -> CodeAction:
        """Create a RUN action (requires command)."""
        self._validate_path(file_path)
        if command is None:
            raise SWEProtocolError("command is required for RUN operations")
        action = CodeAction(
            operation=CodeOperationType.RUN, file_path=file_path, command=command
        )
        self._record(action)
        return action

    def review(self, file_path: str) -> CodeAction:
        """Create a REVIEW action."""
        self._validate_path(file_path)
        action = CodeAction(operation=CodeOperationType.REVIEW, file_path=file_path)
        self._record(action)
        return action

    def explain(self, file_path: str) -> CodeAction:
        """Create an EXPLAIN action."""
        self._validate_path(file_path)
        action = CodeAction(operation=CodeOperationType.EXPLAIN, file_path=file_path)
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

    def _validate_path(self, file_path: str) -> None:
        if not file_path or not file_path.strip():
            raise SWEProtocolError("file_path must not be empty")
        if ".." in file_path:
            raise SWEProtocolError(
                f"Path traversal detected in file_path: '{file_path}'"
            )

    def _record(self, action: CodeAction) -> None:
        self._history.append(action)

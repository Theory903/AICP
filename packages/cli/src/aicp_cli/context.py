"""CLI runtime context.

Provides a unified way to load project state and runtime-backed services.
Supports both standalone mode (local store) and server mode (HTTP client).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import click
import requests

from aicp.executor import AicpExecutor
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.executor import Executor
from aicp.project_loader import LoadedProject, load_project
from aicp_runtime.persistence import RuntimeStore
from aicp_runtime.services import ApprovalService, AuditService


@dataclass(slots=True)
class RuntimeContext:
    """Shared runtime context for CLI commands."""

    project: LoadedProject
    store: RuntimeStore
    audit: AuditService
    approvals: ApprovalService

    @property
    def config(self):
        """Shortcut to the active project config."""
        return self.project.config

    @property
    def executor(self) -> Executor:
        """Shortcut to the active project executor."""
        return self.project.executor

    @property
    def policy_engine(self):
        """Shortcut to the active project policy engine."""
        return self.project.policy_engine

    @property
    def repository(self) -> CapabilityProvider:
        """Shortcut to the active capability repository."""
        return self.project.repository

    @property
    def capabilities(self) -> list:
        """Shortcut to loaded project capabilities."""
        return self.project.capabilities


@dataclass(slots=True)
class RuntimeClient:
    """HTTP client for talking to a running AICP server."""

    base_url: str
    session: requests.Session = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def close(self) -> None:
        self.session.close()

    def execute(self, capability_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a capability via the server."""
        response = self.session.post(
            f"{self.base_url}/v1/execute",
            json={"capability_name": capability_name, "arguments": arguments},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_approvals(self, status: str = "pending") -> list[dict[str, Any]]:
        """List approvals from the server."""
        response = self.session.get(
            f"{self.base_url}/approvals",
            params={"status": status},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_approval(self, approval_id: str) -> dict[str, Any]:
        """Get a specific approval."""
        response = self.session.get(
            f"{self.base_url}/approvals/{approval_id}",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def decide_approval(
        self,
        approval_id: str,
        decision: str,
        approver: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Approve or reject an approval request."""
        response = self.session.post(
            f"{self.base_url}/approvals/{approval_id}/decide",
            json={"decision": decision, "approver": approver, "reason": reason},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def list_sessions(self) -> list[dict[str, Any]]:
        """List sessions."""
        response = self.session.get(f"{self.base_url}/v1/sessions", timeout=10)
        response.raise_for_status()
        return response.json()

    def list_interactions(self) -> list[dict[str, Any]]:
        """List interactions."""
        response = self.session.get(f"{self.base_url}/v1/interactions", timeout=10)
        response.raise_for_status()
        return response.json()

    def get_capabilities(self) -> list[dict[str, Any]]:
        """Get capabilities."""
        response = self.session.get(f"{self.base_url}/.well-known/aicp", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("capabilities", [])

    def rank_capabilities(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Rank capabilities."""
        response = self.session.get(
            f"{self.base_url}/v1/capabilities/rank",
            params={"query": query, "limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_provider_health(self) -> list[dict[str, Any]]:
        """Get provider health."""
        response = self.session.get(f"{self.base_url}/providers/health", timeout=10)
        response.raise_for_status()
        return response.json()

    def list_executions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List executions."""
        response = self.session.get(
            f"{self.base_url}/v1/executions",
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def find_approved_for_intent(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Find an approved approval for matching intent."""
        try:
            response = self.session.post(
                f"{self.base_url}/approvals/find-by-intent",
                json={
                    "capability_name": capability_name,
                    "arguments": arguments or {},
                    "context": context or {},
                },
                timeout=10,
            )
            if response.status_code == 404:
                return None
            if response.status_code >= 400:
                return None
            return response.json()
        except Exception:
            return None


def get_runtime_context(
    project_root: str | Path | None = None,
    server_url: str | None = None,
) -> RuntimeContext:
    """Load the active project and initialize runtime-backed services.

    If server_url is provided, connects to a running AICP server instead of
    creating local stores. This enables the CLI to work with the server's
    persisted state (approvals, executions, sessions).

    Args:
        project_root: Optional project root. Defaults to the current working directory.
        server_url: Optional server URL (e.g., http://127.0.0.1:8000). If provided,
                    CLI will use HTTP client to talk to server instead of local store.

    Returns:
        Fully wired RuntimeContext.
    """
    root = Path(project_root or os.getcwd()).resolve()

    project = load_project(root)

    store = _create_runtime_store(
        root=root,
        store_backend=project.config.runtime.store_backend,
        store_path=project.config.runtime.store_path,
    )

    audit = AuditService(store)
    approvals = ApprovalService(store)

    _bind_runtime_services(project, approvals)

    return RuntimeContext(
        project=project,
        store=store,
        audit=audit,
        approvals=approvals,
    )


def get_server_client(server_url: str | None = None) -> RuntimeClient | None:
    """Try to connect to a running AICP server.

    Args:
        server_url: Server URL to connect to. If None, tries default http://127.0.0.1:8000

    Returns:
        RuntimeClient if server is running and responding, None otherwise.
    """
    url = server_url or os.environ.get("AICP_SERVER_URL") or "http://127.0.0.1:8000"

    try:
        response = requests.get(f"{url}/health", timeout=2)
        if response.status_code < 500:
            return RuntimeClient(base_url=url)
    except requests.RequestException:
        pass

    try:
        response = requests.get(f"{url}/.well-known/aicp", timeout=2)
        if response.status_code == 200:
            return RuntimeClient(base_url=url)
    except requests.RequestException:
        pass

    return None


def require_runtime_context(project_root: str | Path | None = None) -> RuntimeContext:
    """Load runtime context or raise a user-facing CLI error."""
    root = Path(project_root or os.getcwd()).resolve()

    try:
        return get_runtime_context(root)
    except FileNotFoundError as exc:
        raise click.ClickException(
            f"No AICP project found in {root}. Expected {root / 'aicp.yaml'}. "
            "Run 'aicp init' or change into a directory that already contains an AICP project."
        ) from exc


def _create_runtime_store(
    *,
    root: Path,
    store_backend: str,
    store_path: str | None,
) -> RuntimeStore:
    """Create the configured runtime persistence store."""
    backend = (store_backend or "memory").strip().lower()

    if backend == "sqlite":
        from aicp_runtime.persistence.sqlite import SqliteRuntimeStore

        db_path = Path(store_path) if store_path else root / ".aicp" / "runtime.db"
        db_path = _resolve_path(root, db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return cast(RuntimeStore, SqliteRuntimeStore(str(db_path)))

    if backend == "file":
        from aicp_runtime.persistence.file import FileRuntimeStore

        dir_path = Path(store_path) if store_path else root / ".aicp" / "runtime"
        dir_path = _resolve_path(root, dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return cast(RuntimeStore, FileRuntimeStore(str(dir_path)))

    if backend == "memory":
        from aicp_runtime.persistence.memory import InMemoryRuntimeStore

        return cast(RuntimeStore, InMemoryRuntimeStore())

    raise RuntimeError(
        f"Unsupported runtime store backend: {store_backend!r}. "
        "Expected one of: memory, file, sqlite."
    )


def _resolve_path(root: Path, path: Path) -> Path:
    """Resolve a configured path relative to the project root when needed."""
    resolved = path if path.is_absolute() else (root / path)
    return resolved.resolve()


def _bind_runtime_services(
    project: LoadedProject,
    approvals: ApprovalService,
) -> None:
    """Attach runtime-backed services to the loaded project where appropriate.

    This keeps CLI execution flows coherent:
    - `aicp run` uses the same approval service as `aicp appr ...`
    """
    executor = project.executor

    if isinstance(executor, AicpExecutor):
        cast(Any, executor)._approval_service = approvals

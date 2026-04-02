"""Runtime app factory."""

from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from aicp.implementations import InMemoryCapabilityRepository
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.policy_engine import PolicyEngine
from fastapi import FastAPI

from aicp_runtime.api.routes.approvals import build_approvals_router
from aicp_runtime.api.routes.console import build_console_router
from aicp_runtime.api.routes.discover import build_discovery_router
from aicp_runtime.api.routes.execute import build_execution_router
from aicp_runtime.api.routes.history import build_history_router
from aicp_runtime.api.routes.providers import build_provider_health_router
from aicp_runtime.api.routes.v1 import build_v1_router
from aicp_runtime.api.routes.workflows import build_workflows_router
from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.audit import AuditService
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService
from aicp_runtime.services.interactions import InteractionStateService
from aicp_runtime.services.provider_health import ProviderHealthService
from aicp_runtime.services.sessions import SessionService
from aicp_runtime.services.workflows import WorkflowService


@dataclass(slots=True)
class RuntimeServices:
    """Typed runtime service container."""

    audit_service: AuditService
    approval_service: ApprovalService
    discovery_service: DiscoveryService
    execution_service: ExecutionService
    interaction_service: InteractionStateService
    provider_health_service: ProviderHealthService
    session_service: SessionService
    workflow_service: WorkflowService


def create_app(
    capability_provider: CapabilityProvider | None = None,
    policy_engine: PolicyEngine | None = None,
    store_path: str | Path | None = None,
    store_backend: str = "memory",
) -> FastAPI:
    """Create a FastAPI app for the AICP runtime."""
    provider = capability_provider or InMemoryCapabilityRepository("runtime")
    runtime_store = _create_runtime_store(
        store_backend=store_backend,
        store_path=store_path,
    )
    services = _build_services(
        provider=provider,
        policy_engine=policy_engine,
        runtime_store=runtime_store,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await _close_runtime_store(runtime_store)

    app = FastAPI(
        title="AICP Runtime",
        version="0.1.1",
        description="HTTP runtime for discovery, execution, approvals, workflows, and audit history.",
        lifespan=lifespan,
    )

    _attach_state(
        app,
        runtime_store=runtime_store,
        provider=provider,
        policy_engine=policy_engine,
        services=services,
        store_backend=store_backend,
        store_path=store_path,
    )
    _register_routes(app, services)

    return app


def _create_runtime_store(
    *,
    store_backend: str,
    store_path: str | Path | None,
) -> RuntimeStore:
    """Create the configured runtime store."""
    backend = (store_backend or "memory").strip().lower()

    if backend == "memory" and store_path is not None:
        backend = _infer_store_backend(Path(store_path))

    if backend == "memory":
        return InMemoryRuntimeStore()

    if backend == "sqlite":
        path = Path(store_path) if store_path else Path(".aicp-runtime.db")
        return SqliteRuntimeStore(path)

    if backend == "file":
        path = Path(store_path) if store_path else Path(".aicp-runtime")
        return FileRuntimeStore(path)

    raise ValueError(
        f"Unsupported store_backend: {store_backend!r}. "
        "Expected one of: memory, file, sqlite."
    )


def _infer_store_backend(store_path: Path) -> str:
    """Infer a durable backend from the provided path."""
    if store_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        return "sqlite"
    return "file"


def _build_services(
    *,
    provider: CapabilityProvider,
    policy_engine: PolicyEngine | None,
    runtime_store: RuntimeStore,
) -> RuntimeServices:
    """Construct runtime services."""
    audit_service = AuditService(runtime_store)
    approval_service = ApprovalService(runtime_store, audit_service, provider)
    session_service = SessionService(runtime_store, audit_service)
    interaction_service = InteractionStateService(runtime_store, audit_service)
    discovery_service = DiscoveryService(provider)
    provider_health_service = ProviderHealthService(runtime_store, provider)
    execution_service = ExecutionService(
        provider,
        policy_engine,
        runtime_store,
        approval_service,
        interaction_service,
        session_service,
    )
    workflow_service = WorkflowService(
        provider,
        runtime_store,
        policy_engine,
        approval_service,
        audit_service,
    )

    return RuntimeServices(
        audit_service=audit_service,
        approval_service=approval_service,
        discovery_service=discovery_service,
        execution_service=execution_service,
        interaction_service=interaction_service,
        provider_health_service=provider_health_service,
        session_service=session_service,
        workflow_service=workflow_service,
    )


def _attach_state(
    app: FastAPI,
    *,
    runtime_store: RuntimeStore,
    provider: CapabilityProvider,
    policy_engine: PolicyEngine | None,
    services: RuntimeServices,
    store_backend: str,
    store_path: str | Path | None,
) -> None:
    """Attach runtime objects to FastAPI state."""
    app.state.runtime_store = runtime_store
    app.state.capability_provider = provider
    app.state.policy_engine = policy_engine
    app.state.store_backend = store_backend
    app.state.store_path = str(store_path) if store_path is not None else None

    app.state.audit_service = services.audit_service
    app.state.approval_service = services.approval_service
    app.state.discovery_service = services.discovery_service
    app.state.execution_service = services.execution_service
    app.state.interaction_service = services.interaction_service
    app.state.provider_health_service = services.provider_health_service
    app.state.session_service = services.session_service
    app.state.workflow_service = services.workflow_service


def _register_routes(app: FastAPI, services: RuntimeServices) -> None:
    """Register API routers."""
    app.include_router(build_discovery_router(services.discovery_service))
    app.include_router(build_console_router())
    app.include_router(build_execution_router(services.execution_service))
    app.include_router(build_workflows_router(services.workflow_service))
    app.include_router(build_approvals_router(services.approval_service))
    app.include_router(build_provider_health_router(services.provider_health_service))
    app.include_router(
        build_v1_router(
            services.discovery_service,
            services.execution_service,
            services.approval_service,
            services.interaction_service,
            services.session_service,
            services.workflow_service,
        )
    )
    app.include_router(build_history_router(services.audit_service))


async def _close_runtime_store(runtime_store: RuntimeStore) -> None:
    """Gracefully close the runtime store if it exposes a close hook."""
    close = getattr(runtime_store, "close", None)
    if not callable(close):
        return

    result = close()
    if inspect.isawaitable(result):
        await result

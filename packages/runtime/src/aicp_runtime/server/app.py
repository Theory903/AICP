"""Runtime app factory."""

from pathlib import Path

from fastapi import FastAPI

from aicp.implementations import InMemoryCapabilityRepository
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.policy_engine import PolicyEngine

from aicp_runtime.api.routes.approvals import build_approvals_router
from aicp_runtime.api.routes.discover import build_discover_router
from aicp_runtime.api.routes.execute import build_execute_router
from aicp_runtime.api.routes.history import build_history_router
from aicp_runtime.api.routes.workflows import build_workflows_router
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.audit import AuditService
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService
from aicp_runtime.services.workflows import WorkflowService


def create_app(
    capability_provider: CapabilityProvider | None = None,
    policy_engine: PolicyEngine | None = None,
    store_path: str | Path | None = None,
    store_backend: str = "memory",
) -> FastAPI:
    """Create a FastAPI app for the AICP runtime."""
    provider = capability_provider or InMemoryCapabilityRepository("runtime")
    if store_backend == "sqlite":
        runtime_store = SqliteRuntimeStore(store_path or ".aicp-runtime.db")
    elif store_path:
        runtime_store = FileRuntimeStore(store_path)
    else:
        runtime_store = InMemoryRuntimeStore()

    audit_service = AuditService(runtime_store)
    approval_service = ApprovalService(runtime_store, audit_service)
    discovery_service = DiscoveryService(provider)
    execution_service = ExecutionService(provider, policy_engine, runtime_store)
    workflow_service = WorkflowService(
        provider,
        runtime_store,
        policy_engine,
        approval_service,
        audit_service,
    )

    app = FastAPI(title="AICP Runtime")
    app.state.runtime_store = runtime_store
    app.state.audit_service = audit_service
    app.state.approval_service = approval_service
    app.state.discovery_service = discovery_service
    app.state.execution_service = execution_service
    app.state.workflow_service = workflow_service
    app.include_router(build_discover_router(discovery_service))
    app.include_router(build_execute_router(execution_service))
    app.include_router(build_workflows_router(workflow_service))
    app.include_router(build_approvals_router(approval_service))
    app.include_router(build_history_router(audit_service))
    return app

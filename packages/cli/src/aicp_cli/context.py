"""CLI Runtime Context.

Provides a unified way to load project state and persistent services.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from aicp.project_loader import LoadedProject, load_project
from aicp_runtime.persistence import RuntimeStore
from aicp_runtime.services import ApprovalService, AuditService


@dataclass
class RuntimeContext:
    """Shared context for CLI commands."""
    project: LoadedProject
    store: RuntimeStore
    audit: AuditService
    approvals: ApprovalService

    @property
    def config(self):
        return self.project.config


def get_runtime_context(project_root: str | Path | None = None) -> RuntimeContext:
    """Initialize and return the full runtime context for the active project."""
    root = Path(project_root or os.getcwd())
    
    # 1. Load the core project (config, caps, repo, executor)
    project = load_project(root)
    config = project.config
    
    # 2. Resolve Persistence Store
    store_backend = config.runtime.store_backend
    store_path = config.runtime.store_path
    
    if store_backend == "sqlite":
        from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
        # Default to .aicp/runtime.db if no path provided
        path = store_path or root / ".aicp" / "runtime.db"
        store = SqliteRuntimeStore(path)
    elif store_backend == "file":
        from aicp_runtime.persistence.file import FileRuntimeStore
        path = store_path or root / ".aicp" / "runtime"
        store = FileRuntimeStore(path)
    else:
        # Default to memory (non-persistent)
        from aicp_runtime.persistence.memory import InMemoryRuntimeStore
        store = InMemoryRuntimeStore()
    
    # 3. Initialize Services with the shared store
    audit = AuditService(store)
    approvals = ApprovalService(store)
    
    return RuntimeContext(
        project=project,
        store=store,
        audit=audit,
        approvals=approvals
    )

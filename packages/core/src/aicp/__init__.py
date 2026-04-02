"""AICP Core public package surface.

AICP (AI Capability Protocol) provides protocol models, execution contracts,
policy/workflow abstractions, and default in-memory implementations for local use.
"""

from __future__ import annotations

__version__ = "0.1.1"

# Configuration
# API management
from .api import VersionManager, lifespan_context

# Approval (HITL)
from .approval import (
    ApprovalContext,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalRisk,
    ApprovalStatus,
    calculate_risk,
)
from .approval_service import ApprovalService, ApprovalStore, InMemoryApprovalStore

# Capability models
from .capability import (
    AuthRequirement,
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    ProviderInfo,
)
from .config import AicpProjectConfig, load_project_config

# Errors
from .errors import AicpError, DiscoveryError, ExecutionError, PolicyError, ValidationError

# Execution
from .executor import AicpExecutor

# Policy
from .implementations.policy import ConfigPolicyEngine, DefaultPolicyEngine

# Workflow
from .implementations.workflow import DefaultWorkflowRuntime
from .interfaces.executor import ExecutionResult, ExecutionStatus, Executor
from .interfaces.policy_engine import (
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
)
from .interfaces.workflow_runtime import (
    Step,
    StepResult,
    StepStatus,
    WorkflowRuntime,
    WorkflowState,
    WorkflowStatus,
)

# Observability
from .observability import get_logger, get_metrics, get_tracer

# Project loading
from .project_loader import LoadedProject, load_project

# Registry & validation
from .registry import AicpRegistry
from .validator import AicpValidator

# Optional adapters
try:
    from .adapters import HttpExecutionAdapter, McpAdapter
except ImportError:
    HttpExecutionAdapter = None
    McpAdapter = None

__all__ = [
    "__version__",
    # Config
    "AicpProjectConfig",
    "load_project_config",
    # Capability
    "Capability",
    "CapabilityKind",
    "AuthRequirement",
    "InputSchema",
    "OutputSchema",
    "ProviderInfo",
    # Registry & validation
    "AicpRegistry",
    "AicpValidator",
    # Execution
    "AicpExecutor",
    "Executor",
    "ExecutionResult",
    "ExecutionStatus",
    # Policy
    "Policy",
    "PolicyCondition",
    "PolicyDecision",
    "PolicyEffect",
    "PolicyEngine",
    "PolicySubject",
    "DefaultPolicyEngine",
    "ConfigPolicyEngine",
    # Workflow
    "Step",
    "StepStatus",
    "StepResult",
    "WorkflowRuntime",
    "WorkflowState",
    "WorkflowStatus",
    "DefaultWorkflowRuntime",
    # Approval
    "ApprovalContext",
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalRisk",
    "ApprovalStatus",
    "ApprovalService",
    "ApprovalStore",
    "InMemoryApprovalStore",
    "calculate_risk",
    # Project loader
    "LoadedProject",
    "load_project",
    # Errors
    "AicpError",
    "ValidationError",
    "DiscoveryError",
    "ExecutionError",
    "PolicyError",
    # Observability
    "get_logger",
    "get_metrics",
    "get_tracer",
    # API
    "VersionManager",
    "lifespan_context",
    # Adapters
    "HttpExecutionAdapter",
    "McpAdapter",
]

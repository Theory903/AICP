"""AICP Core - Protocol domain models and validation.

AICP (AI Capability Protocol) is a standard for capability-aware,
workflow-aware, and policy-aware AI execution.

Main exports:
- Capability models and kinds
- Policy engine interfaces and implementations
- Registry for managing capabilities and policies
- Executor for running capabilities with policy enforcement
- Adapters for HTTP, MCP, and other protocols
"""

__version__ = "0.1.0"

# Capability models
# Adapters
try:
    from aicp.adapters import HttpExecutionAdapter, McpAdapter
except ImportError:
    HttpExecutionAdapter = None
    McpAdapter = None

from aicp.capability import (
    Capability,
    CapabilityKind,
    ContinuationSpec,
    InputSchema,
    OutputSchema,
    PolicyRef,
    RenderSpec,
)

# Error classes
from aicp.errors import (
    AicpError,
    DiscoveryError,
    ExecutionError,
    PolicyError,
    ValidationError,
)

# Core components
from aicp.executor import AicpExecutor

# Implementations
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.implementations.workflow import DefaultWorkflowRuntime

# Interfaces
from aicp.interfaces import (
    CapabilityProvider,
    DiscoveredCapability,
    DiscoverySource,
    ExecutionResult,
    ExecutionStatus,
    Executor,
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
    Renderer,
    RenderHints,
    StepResult,
    WorkflowRuntime,
    WorkflowState,
)
from aicp.registry import AicpRegistry
from aicp.validator import AicpValidator
from aicp.validator import ValidationError as SchemaValidationError

__all__ = [
    # Version
    "__version__",
    # Capability models
    "Capability",
    "CapabilityKind",
    "ContinuationSpec",
    "InputSchema",
    "OutputSchema",
    "PolicyRef",
    "RenderSpec",
    # Error classes
    "AicpError",
    "DiscoveryError",
    "ExecutionError",
    "PolicyError",
    "ValidationError",
    "SchemaValidationError",
    # Interfaces
    "CapabilityProvider",
    "DiscoverySource",
    "DiscoveredCapability",
    "Executor",
    "ExecutionResult",
    "ExecutionStatus",
    "Policy",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyEffect",
    "PolicySubject",
    "PolicyCondition",
    "Renderer",
    "RenderHints",
    "StepResult",
    "WorkflowRuntime",
    "WorkflowState",
    # Implementations
    "InMemoryCapabilityRepository",
    "DefaultPolicyEngine",
    "DefaultWorkflowRuntime",
    # Core components
    "AicpRegistry",
    "AicpValidator",
    "AicpExecutor",
    # Adapters
    "HttpExecutionAdapter",
    "McpAdapter",
]

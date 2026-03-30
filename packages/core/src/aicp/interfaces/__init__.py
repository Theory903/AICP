"""AICP core interfaces.

These interfaces define the contracts for the AICP runtime. They are designed
to be pluggable, allowing different implementations for various protocols,
discovery sources, and execution strategies.
"""

from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.discovery_source import DiscoveredCapability, DiscoverySource
from aicp.interfaces.executor import (
    ExecutionResult,
    ExecutionStatus,
    Executor,
)
from aicp.interfaces.policy_engine import (
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
)
from aicp.interfaces.renderer import Renderer, RenderHints
from aicp.interfaces.workflow_runtime import (
    Step,
    StepResult,
    StepStatus,
    WorkflowError,
    WorkflowRuntime,
    WorkflowState,
    WorkflowStatus,
)

__all__ = [
    # Capability provider
    "CapabilityProvider",
    # Policy engine
    "PolicyEngine",
    "Policy",
    "PolicyDecision",
    "PolicyEffect",
    "PolicySubject",
    "PolicyCondition",
    # Workflow runtime
    "WorkflowRuntime",
    "WorkflowState",
    "WorkflowError",
    "Step",
    "StepResult",
    "StepStatus",
    "WorkflowStatus",
    # Executor
    "Executor",
    "ExecutionResult",
    "ExecutionStatus",
    # Renderer
    "Renderer",
    "RenderHints",
    # Discovery
    "DiscoverySource",
    "DiscoveredCapability",
]

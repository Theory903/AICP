"""AICP core interfaces.

These interfaces define the contracts for the AICP runtime. They are intended
to be pluggable, allowing different implementations for discovery, execution,
policy evaluation, rendering, and workflow orchestration.
"""

from __future__ import annotations

from .capability_provider import CapabilityProvider
from .discovery_source import DiscoveredCapability, DiscoverySource
from .executor import ExecutionResult, ExecutionStatus, Executor
from .policy_engine import (
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEngine,
    PolicySubject,
)
from .renderer import RenderHints, Renderer
from .workflow_runtime import (
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
    # Discovery
    "DiscoverySource",
    "DiscoveredCapability",
    # Executor
    "Executor",
    "ExecutionResult",
    "ExecutionStatus",
    # Policy engine
    "PolicyEngine",
    "Policy",
    "PolicyDecision",
    "PolicyEffect",
    "PolicySubject",
    "PolicyCondition",
    # Renderer
    "Renderer",
    "RenderHints",
    # Workflow runtime
    "WorkflowRuntime",
    "WorkflowState",
    "WorkflowError",
    "Step",
    "StepResult",
    "StepStatus",
    "WorkflowStatus",
]
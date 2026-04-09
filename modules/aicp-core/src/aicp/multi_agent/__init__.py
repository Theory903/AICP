"""Multi-Agent orchestration for AICP.

Exports:
- Agent types and states
- Message bus for inter-agent communication
- Agent hierarchy management
- Hook system for lifecycle events
- Task management
"""

from .hierarchy import (
    Agent,
    AgentCommunicationBus,
    AgentContext,
    AgentHierarchy,
    AgentHierarchyError,
    AgentHooks,
    AgentMessage,
    AgentNotFoundError,
    AgentState,
    AgentTask,
    AgentType,
    HookEvent,
    HookResult,
    MessagePriority,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentHierarchy",
    "AgentHierarchyError",
    "AgentMessage",
    "AgentNotFoundError",
    "AgentState",
    "AgentTask",
    "AgentType",
    "AgentCommunicationBus",
    "AgentHooks",
    "HookEvent",
    "HookResult",
    "MessagePriority",
]

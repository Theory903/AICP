"""Multi-Agent orchestration for AICP.

This module provides:
- Agent hierarchy (Orchestrator → Specialist → Worker)
- Message bus for inter-agent communication
- Lifecycle hooks for audit and state management
- Permission-based execution control

Patterns adapted from:
- nanobot (hooks, lifecycle)
- claw-code-ref (session state, tool registry)
- corsair (permission engine)
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import Callable, Coroutine
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aicp.errors import AicpError

# ============================================================================
# Core Models
# ============================================================================


class AgentType(str, Enum):
    """Agent types in the hierarchy."""
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    WORKER = "worker"


class AgentState(str, Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class MessagePriority(str, Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentMessage(BaseModel):
    """Message between agents."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str
    receiver_id: str | None = None  # None = broadcast
    topic: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: str | None = None  # For request/response matching
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reply_to: str | None = None  # Message ID to reply to

    model_config = ConfigDict(use_enum_values=True)


class AgentContext(BaseModel):
    """Execution context for an agent."""
    session_id: str
    principal_id: str
    org_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Task assigned to an agent."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    capability_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: AgentContext
    assigned_to: str | None = None
    status: AgentState = AgentState.IDLE
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Agent(BaseModel):
    """Agent in the hierarchy."""
    id: str
    type: AgentType
    name: str
    description: str | None = None
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)  # capability names
    state: AgentState = AgentState.IDLE
    current_task: str | None = None  # task_id
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Hooks System (adapted from corsair/nanobot)
# ============================================================================


class HookEvent(str, Enum):
    """Events that triggers hooks."""
    BEFORE_TASK = "before_task"
    AFTER_TASK = "after_task"
    BEFORE_THINK = "before_think"
    AFTER_THINK = "after_think"
    BEFORE_EXECUTE = "before_execute"
    AFTER_EXECUTE = "after_execute"
    ON_ERROR = "on_error"
    ON_STATE_CHANGE = "on_state_change"


class HookResult(BaseModel):
    """Result of hook execution."""
    allowed: bool = True
    modified_payload: dict[str, Any] | None = None
    error: str | None = None
    continue_chain: bool = True


HookCallable = Callable[[AgentTask, AgentContext], Coroutine[Any, Any, HookResult]]


class AgentHooks(BaseModel):
    """Hook registry for agent lifecycle."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    hooks_store: dict[HookEvent, list[HookCallable]] = Field(default_factory=dict)

    def register(self, event: HookEvent, hook: HookCallable) -> None:
        if event not in self.hooks_store:
            self.hooks_store[event] = []
        self.hooks_store[event].append(hook)

    def unregister(self, event: HookEvent, hook: HookCallable) -> None:
        if event in self.hooks_store:
            self.hooks_store[event].remove(hook)

    async def trigger(self, event: HookEvent, task: AgentTask, ctx: AgentContext) -> HookResult:
        result = HookResult(allowed=True, continue_chain=True)

        hooks = self.hooks_store.get(event, [])
        for hook in hooks:
            try:
                hook_result = await hook(task, ctx)
                if not hook_result.allowed:
                    result.allowed = False
                    result.error = hook_result.error
                    result.continue_chain = False
                    break
                if hook_result.modified_payload:
                    result.modified_payload = hook_result.modified_payload
            except Exception as e:
                result.allowed = False
                result.error = str(e)
                result.continue_chain = False
                break

        return result


# ============================================================================
# Message Bus (adapted from nanobot)
# ============================================================================


class AgentCommunicationBus(BaseModel):
    """Pub/Sub message bus for inter-agent communication.

    Provides decoupled communication between agents via topics.
    Supports both point-to-point and broadcast messaging.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    subscriptions_store: dict[str, list[Callable[[AgentMessage], Coroutine[Any, Any, None]]]] = Field(
        default_factory=dict,
    )
    message_queue_store: asyncio.Queue = Field(default_factory=asyncio.Queue)
    running_flag: bool = False

    def subscribe(self, topic: str, callback: Callable[[AgentMessage], Coroutine[Any, Any, None]]) -> None:
        if topic not in self.subscriptions_store:
            self.subscriptions_store[topic] = []
        if callback not in self.subscriptions_store[topic]:
            self.subscriptions_store[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[AgentMessage], Coroutine[Any, Any, None]]) -> None:
        if topic in self.subscriptions_store:
            self.subscriptions_store[topic] = [cb for cb in self.subscriptions_store[topic] if cb != callback]

    async def publish(self, message: AgentMessage) -> None:
        await self.message_queue_store.put(message)

        callbacks = self.subscriptions_store.get(message.topic, [])
        for callback in callbacks:
            with contextlib.suppress(Exception):
                await callback(message)

    async def broadcast(self, topic: str, payload: dict[str, Any], sender_id: str) -> AgentMessage:
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=None,
            topic=topic,
            payload=payload,
        )
        await self.publish(message)
        return message

    async def send_to(self, receiver_id: str, topic: str, payload: dict[str, Any], sender_id: str) -> AgentMessage:
        message = AgentMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            topic=topic,
            payload=payload,
        )
        await self.publish(message)
        return message

    async def start_dispatcher(self) -> None:
        self.running_flag = True
        while self.running_flag:
            try:
                message = await asyncio.wait_for(self.message_queue_store.get(), timeout=1.0)
                callbacks = self.subscriptions_store.get(message.topic, [])
                for callback in callbacks:
                    with contextlib.suppress(Exception):
                        await callback(message)
            except asyncio.TimeoutError:
                continue
            except Exception:
                pass

    def stop_dispatcher(self) -> None:
        self.running_flag = False


# ============================================================================
# Agent Hierarchy
# ============================================================================


class AgentHierarchyError(AicpError):
    """Errors in agent hierarchy operations."""
    pass


class AgentNotFoundError(AgentHierarchyError):
    """Agent not found."""
    pass


class AgentHierarchy(BaseModel):
    """Manages agent hierarchy and lifecycle.

    Provides:
    - Create/manage agents (Orchestrator → Specialist → Worker)
    - Task assignment and execution
    - State management
    - Hook system integration
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    agents: dict[str, Agent] = Field(default_factory=dict)
    tasks: dict[str, AgentTask] = Field(default_factory=dict)
    bus: AgentCommunicationBus = Field(default_factory=AgentCommunicationBus)
    hooks: AgentHooks = Field(default_factory=AgentHooks)
    lock_store: asyncio.Lock = Field(default_factory=asyncio.Lock)

    def create_agent(
        self,
        id: str,
        name: str,
        agent_type: AgentType,
        parent_id: str | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        """Create a new agent in the hierarchy."""
        if id in self.agents:
            raise AgentHierarchyError(f"Agent {id} already exists")

        # Validate parent exists if specified
        if parent_id and parent_id not in self.agents:
            raise AgentNotFoundError(f"Parent agent {parent_id} not found")

        agent = Agent(
            id=id,
            name=name,
            type=agent_type,
            parent_id=parent_id,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )

        self.agents[id] = agent

        # Update parent's children
        if parent_id:
            self.agents[parent_id].children.append(id)

        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_children(self, agent_id: str) -> list[Agent]:
        """Get all children of an agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return []
        return [self.agents[cid] for cid in agent.children if cid in self.agents]

    def get_orchestrators(self) -> list[Agent]:
        """Get all orchestrator agents."""
        return [a for a in self.agents.values() if a.type == AgentType.ORCHESTRATOR]

    def get_specialists(self) -> list[Agent]:
        """Get all specialist agents."""
        return [a for a in self.agents.values() if a.type == AgentType.SPECIALIST]

    def get_workers(self) -> list[Agent]:
        """Get all worker agents."""
        return [a for a in self.agents.values() if a.type == AgentType.WORKER]

    async def assign_task(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: AgentContext,
        assignee_id: str | None = None,
    ) -> AgentTask:
        """Assign a task to an agent."""
        async with self.lock_store:
            task = AgentTask(
                capability_name=capability_name,
                arguments=arguments,
                context=context,
                assigned_to=assignee_id,
            )
            self.tasks[task.id] = task

        # Notify via bus
        await self.bus.broadcast(
            topic="task.assigned",
            payload={"task_id": task.id, "capability": capability_name},
            sender_id=assignee_id or "system",
        )

        return task

    async def execute_task(
        self,
        task_id: str,
        executor: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
    ) -> AgentTask:
        """Execute a task using the provided executor."""
        task = self.tasks.get(task_id)
        if not task:
            raise AgentHierarchyError(f"Task {task_id} not found")

        agent = self.get_agent(task.assigned_to) if task.assigned_to else None

        # Update state
        if agent:
            agent.state = AgentState.EXECUTING
            agent.current_task = task_id
            task.started_at = datetime.utcnow()

        # Trigger before hooks
        hook_result = await self.hooks.trigger(HookEvent.BEFORE_TASK, task, task.context)
        if not hook_result.allowed:
            task.status = AgentState.FAILED
            task.error = hook_result.error or "Hook denied execution"
            return task

        # Apply hook modifications
        if hook_result.modified_payload:
            task.arguments.update(hook_result.modified_payload)

        try:
            # Execute
            result = await executor(task.capability_name, task.arguments)
            task.result = result
            task.status = AgentState.COMPLETED

            # Trigger after hooks
            await self.hooks.trigger(HookEvent.AFTER_TASK, task, task.context)

        except Exception as e:
            task.status = AgentState.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            # Trigger error hooks
            await self.hooks.trigger(HookEvent.ON_ERROR, task, task.context)

        finally:
            task.completed_at = datetime.utcnow()
            if agent:
                agent.state = AgentState.IDLE
                agent.current_task = None
                agent.last_active = datetime.utcnow()

        return task

    async def update_state(self, agent_id: str, state: AgentState) -> None:
        """Update agent state and trigger hooks."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        old_state = agent.state
        agent.state = state
        agent.last_active = datetime.utcnow()

        # Trigger state change hooks
        if old_state != state:
            for task in self.tasks.values():
                if task.assigned_to == agent_id:
                    await self.hooks.trigger(HookEvent.ON_STATE_CHANGE, task, task.context)

    def get_task(self, task_id: str) -> AgentTask | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_tasks_for_agent(self, agent_id: str) -> list[AgentTask]:
        """Get all tasks assigned to an agent."""
        return [t for t in self.tasks.values() if t.assigned_to == agent_id]

    def get_pending_tasks(self) -> list[AgentTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks.values() if t.status == AgentState.IDLE]

    def get_active_tasks(self) -> list[AgentTask]:
        """Get all active (non-terminal) tasks."""
        return [t for t in self.tasks.values() if t.status not in (AgentState.COMPLETED, AgentState.FAILED)]

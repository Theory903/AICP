"""White box tests for multi_agent module."""

import asyncio
import pytest
from datetime import datetime

from aicp.multi_agent import (
    Agent, AgentContext, AgentHierarchy, AgentHierarchyError,
    AgentMessage, AgentNotFoundError, AgentState, AgentTask,
    AgentType, AgentCommunicationBus, AgentHooks, HookEvent, HookResult,
    MessagePriority,
)


# ============================================================================
# Agent Model Tests
# ============================================================================


class TestAgentModel:
    def test_create_agent(self):
        agent = Agent(id="test-1", name="Test Agent", type=AgentType.WORKER)
        assert agent.id == "test-1"
        assert agent.name == "Test Agent"
        assert agent.type == AgentType.WORKER
        assert agent.parent_id is None
        assert agent.children == []
        assert agent.state == AgentState.IDLE
        assert agent.capabilities == []

    def test_agent_with_capabilities(self):
        agent = Agent(
            id="spec-1",
            name="Research Specialist",
            type=AgentType.SPECIALIST,
            capabilities=["web.search", "web.fetch"],
        )
        assert len(agent.capabilities) == 2
        assert "web.search" in agent.capabilities

    def test_agent_with_metadata(self):
        agent = Agent(
            id="w-1",
            name="Worker",
            type=AgentType.WORKER,
            metadata={"model": "gpt-4", "temperature": 0.7},
        )
        assert agent.metadata["model"] == "gpt-4"


# ============================================================================
# AgentHierarchy Tests
# ============================================================================


class TestAgentHierarchy:
    def test_create_orchestrator(self):
        hierarchy = AgentHierarchy()
        agent = hierarchy.create_agent(
            id="orch-1",
            name="Main Orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
        )
        assert agent.id == "orch-1"
        assert agent.type == AgentType.ORCHESTRATOR
        assert hierarchy.get_agent("orch-1") is not None

    def test_create_with_parent(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="orch-1", name="Orchestrator", agent_type=AgentType.ORCHESTRATOR)
        specialist = hierarchy.create_agent(
            id="spec-1",
            name="Research Specialist",
            agent_type=AgentType.SPECIALIST,
            parent_id="orch-1",
        )
        assert specialist.parent_id == "orch-1"
        assert "spec-1" in hierarchy.agents["orch-1"].children

    def test_create_duplicate_raises(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="a-1", name="Agent", agent_type=AgentType.WORKER)
        with pytest.raises(AgentHierarchyError, match="already exists"):
            hierarchy.create_agent(id="a-1", name="Agent 2", agent_type=AgentType.WORKER)

    def test_create_with_missing_parent_raises(self):
        hierarchy = AgentHierarchy()
        with pytest.raises(AgentNotFoundError, match="not found"):
            hierarchy.create_agent(id="child", name="Child", agent_type=AgentType.WORKER, parent_id="nonexistent")

    def test_get_children(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="orch-1", name="Orchestrator", agent_type=AgentType.ORCHESTRATOR)
        hierarchy.create_agent(id="spec-1", name="Spec 1", agent_type=AgentType.SPECIALIST, parent_id="orch-1")
        hierarchy.create_agent(id="spec-2", name="Spec 2", agent_type=AgentType.SPECIALIST, parent_id="orch-1")
        
        children = hierarchy.get_children("orch-1")
        assert len(children) == 2
        assert {c.id for c in children} == {"spec-1", "spec-2"}

    def test_get_orchestrators(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="orch-1", name="O1", agent_type=AgentType.ORCHESTRATOR)
        hierarchy.create_agent(id="spec-1", name="S1", agent_type=AgentType.SPECIALIST)
        hierarchy.create_agent(id="orch-2", name="O2", agent_type=AgentType.ORCHESTRATOR)
        
        orchestrators = hierarchy.get_orchestrators()
        assert len(orchestrators) == 2
        assert {a.id for a in orchestrators} == {"orch-1", "orch-2"}

    def test_get_specialists(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="s1", name="S1", agent_type=AgentType.SPECIALIST)
        hierarchy.create_agent(id="w1", name="W1", agent_type=AgentType.WORKER)
        specialists = hierarchy.get_specialists()
        assert len(specialists) == 1
        assert specialists[0].id == "s1"

    def test_get_workers(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="W1", agent_type=AgentType.WORKER)
        hierarchy.create_agent(id="w2", name="W2", agent_type=AgentType.WORKER)
        workers = hierarchy.get_workers()
        assert len(workers) == 2

    def test_get_agent_not_found(self):
        hierarchy = AgentHierarchy()
        assert hierarchy.get_agent("nonexistent") is None


# ============================================================================
# AgentCommunicationBus Tests
# ============================================================================


class TestAgentCommunicationBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_broadcast(self):
        bus = AgentCommunicationBus()
        received = []

        async def handler(message):
            received.append(message)

        bus.subscribe("test.topic", handler)
        await bus.broadcast("test.topic", {"key": "value"}, "sender-1")
        
        assert len(received) == 1
        assert received[0].topic == "test.topic"
        assert received[0].payload == {"key": "value"}
        assert received[0].sender_id == "sender-1"

    @pytest.mark.asyncio
    async def test_send_to_specific_agent(self):
        bus = AgentCommunicationBus()
        received = []

        async def handler(message):
            received.append(message)

        bus.subscribe("task.assign", handler)
        await bus.send_to("agent-1", "task.assign", {"task": "research"}, "orch-1")
        
        assert len(received) == 1
        assert received[0].receiver_id == "agent-1"

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = AgentCommunicationBus()
        received = []

        async def handler(message):
            received.append(message)

        bus.subscribe("topic", handler)
        bus.unsubscribe("topic", handler)
        await bus.broadcast("topic", {"data": "test"}, "sender")
        
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = AgentCommunicationBus()
        received_1 = []
        received_2 = []

        async def handler_1(message):
            received_1.append(message)

        async def handler_2(message):
            received_2.append(message)

        bus.subscribe("shared", handler_1)
        bus.subscribe("shared", handler_2)
        await bus.broadcast("shared", {"msg": "hello"}, "sender")
        
        assert len(received_1) == 1
        assert len(received_2) == 1

    @pytest.mark.asyncio
    async def test_message_priority(self):
        bus = AgentCommunicationBus()
        received = []

        async def handler(message):
            received.append(message)

        bus.subscribe("urgent", handler)
        await bus.broadcast("urgent", {"data": "critical"}, "sender")
        
        assert received[0].priority == MessagePriority.NORMAL

    def test_stop_dispatcher(self):
        bus = AgentCommunicationBus()
        bus.running_flag = True
        bus.stop_dispatcher()
        assert bus.running_flag is False


# ============================================================================
# AgentHooks Tests
# ============================================================================


class TestAgentHooks:
    @pytest.mark.asyncio
    async def test_register_and_trigger(self):
        hooks = AgentHooks()
        triggered = []

        async def my_hook(task, ctx):
            triggered.append(task.capability_name)
            return HookResult(allowed=True)

        hooks.register(HookEvent.BEFORE_TASK, my_hook)
        
        task = AgentTask(
            capability_name="web.search",
            arguments={"query": "test"},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        ctx = AgentContext(session_id="s1", principal_id="p1")
        
        result = await hooks.trigger(HookEvent.BEFORE_TASK, task, ctx)
        
        assert result.allowed is True
        assert len(triggered) == 1
        assert triggered[0] == "web.search"

    @pytest.mark.asyncio
    async def test_hook_denies_execution(self):
        hooks = AgentHooks()

        async def deny_hook(task, ctx):
            return HookResult(allowed=False, error="Policy violation")

        hooks.register(HookEvent.BEFORE_TASK, deny_hook)
        
        task = AgentTask(
            capability_name="payments.transfer",
            arguments={"amount": 100},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        ctx = AgentContext(session_id="s1", principal_id="p1")
        
        result = await hooks.trigger(HookEvent.BEFORE_TASK, task, ctx)
        
        assert result.allowed is False
        assert result.error == "Policy violation"
        assert result.continue_chain is False

    @pytest.mark.asyncio
    async def test_hook_modifies_payload(self):
        hooks = AgentHooks()

        async def modify_hook(task, ctx):
            return HookResult(allowed=True, modified_payload={"extra_key": "added"})

        hooks.register(HookEvent.BEFORE_TASK, modify_hook)
        
        task = AgentTask(
            capability_name="web.search",
            arguments={"query": "test"},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        ctx = AgentContext(session_id="s1", principal_id="p1")
        
        result = await hooks.trigger(HookEvent.BEFORE_TASK, task, ctx)
        
        assert result.allowed is True
        assert result.modified_payload == {"extra_key": "added"}

    @pytest.mark.asyncio
    async def test_hook_exception_stops_chain(self):
        hooks = AgentHooks()

        async def failing_hook(task, ctx):
            raise ValueError("Hook error")

        hooks.register(HookEvent.BEFORE_TASK, failing_hook)
        
        task = AgentTask(
            capability_name="test",
            arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        ctx = AgentContext(session_id="s1", principal_id="p1")
        
        result = await hooks.trigger(HookEvent.BEFORE_TASK, task, ctx)
        
        assert result.allowed is False
        assert result.error is not None
        assert "Hook error" in result.error

    def test_unregister_hook(self):
        hooks = AgentHooks()

        async def my_hook(task, ctx):
            return HookResult(allowed=True)

        hooks.register(HookEvent.BEFORE_TASK, my_hook)
        hooks.unregister(HookEvent.BEFORE_TASK, my_hook)
        
        assert len(hooks.hooks_store.get(HookEvent.BEFORE_TASK, [])) == 0


# ============================================================================
# Task Execution Tests
# ============================================================================


class TestTaskExecution:
    @pytest.mark.asyncio
    async def test_assign_task(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="Worker", agent_type=AgentType.WORKER)
        
        context = AgentContext(session_id="s1", principal_id="p1")
        task = await hierarchy.assign_task(
            capability_name="web.search",
            arguments={"query": "test"},
            context=context,
            assignee_id="w1",
        )
        
        assert task.capability_name == "web.search"
        assert task.assigned_to == "w1"
        assert task.status == AgentState.IDLE
        assert task.id in hierarchy.tasks

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="Worker", agent_type=AgentType.WORKER)
        
        context = AgentContext(session_id="s1", principal_id="p1")
        task = await hierarchy.assign_task(
            capability_name="web.search",
            arguments={"query": "test"},
            context=context,
            assignee_id="w1",
        )

        async def mock_executor(cap_name, args):
            return {"results": ["result1"]}

        result = await hierarchy.execute_task(task.id, mock_executor)
        
        assert result.status == AgentState.COMPLETED
        assert result.result == {"results": ["result1"]}
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_task_failure(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="Worker", agent_type=AgentType.WORKER)
        
        context = AgentContext(session_id="s1", principal_id="p1")
        task = await hierarchy.assign_task(
            capability_name="web.search",
            arguments={"query": "test"},
            context=context,
            assignee_id="w1",
        )

        async def failing_executor(cap_name, args):
            raise RuntimeError("API error")

        result = await hierarchy.execute_task(task.id, failing_executor)
        
        assert result.status == AgentState.FAILED
        assert result.error is not None
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_execute_nonexistent_task(self):
        hierarchy = AgentHierarchy()
        
        async def mock_executor(cap_name, args):
            return {}

        with pytest.raises(AgentHierarchyError, match="not found"):
            await hierarchy.execute_task("nonexistent", mock_executor)

    @pytest.mark.asyncio
    async def test_agent_state_transitions(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="Worker", agent_type=AgentType.WORKER)
        
        assert hierarchy.agents["w1"].state == AgentState.IDLE

        context = AgentContext(session_id="s1", principal_id="p1")
        task = await hierarchy.assign_task(
            capability_name="web.search",
            arguments={},
            context=context,
            assignee_id="w1",
        )

        async def mock_executor(cap_name, args):
            return {}

        await hierarchy.execute_task(task.id, mock_executor)
        
        assert hierarchy.agents["w1"].state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_update_state(self):
        hierarchy = AgentHierarchy()
        hierarchy.create_agent(id="w1", name="Worker", agent_type=AgentType.WORKER)
        
        await hierarchy.update_state("w1", AgentState.THINKING)
        assert hierarchy.agents["w1"].state == AgentState.THINKING

    @pytest.mark.asyncio
    async def test_update_state_nonexistent_agent(self):
        hierarchy = AgentHierarchy()
        
        with pytest.raises(AgentNotFoundError, match="not found"):
            await hierarchy.update_state("nonexistent", AgentState.IDLE)

    def test_get_pending_tasks(self):
        hierarchy = AgentHierarchy()
        t1 = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        hierarchy.tasks["t1"] = t1
        hierarchy.tasks["t2"] = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
            status=AgentState.COMPLETED,
        )
        
        pending = hierarchy.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0].id == t1.id

    def test_get_active_tasks(self):
        hierarchy = AgentHierarchy()
        t1 = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        hierarchy.tasks["t1"] = t1
        hierarchy.tasks["t2"] = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
            status=AgentState.COMPLETED,
        )
        hierarchy.tasks["t3"] = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
            status=AgentState.FAILED,
        )
        
        active = hierarchy.get_active_tasks()
        assert len(active) == 1
        assert active[0].id == t1.id

    def test_get_tasks_for_agent(self):
        hierarchy = AgentHierarchy()
        t1 = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
            assigned_to="w1",
        )
        hierarchy.tasks["t1"] = t1
        hierarchy.tasks["t2"] = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
            assigned_to="w2",
        )
        
        tasks = hierarchy.get_tasks_for_agent("w1")
        assert len(tasks) == 1
        assert tasks[0].id == t1.id

    def test_get_task(self):
        hierarchy = AgentHierarchy()
        t1 = AgentTask(
            capability_name="test", arguments={},
            context=AgentContext(session_id="s1", principal_id="p1"),
        )
        hierarchy.tasks["t1"] = t1
        
        task = hierarchy.get_task("t1")
        assert task is not None
        assert task.id == t1.id
        
        assert hierarchy.get_task("nonexistent") is None

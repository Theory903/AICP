# AICP Multi-Agent

### Agent hierarchy, communication bus, and orchestration for governed AI execution

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/aicp-ai/aicp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)

---

## Overview

**AICP Multi-Agent** provides the agent hierarchy and communication layer for the AI Capability Protocol. It enables orchestrator → specialist → worker patterns with policy-governed task execution, lifecycle hooks, and a pub/sub message bus.

### Features

| Feature | Description |
|---------|-------------|
| **Agent Hierarchy** | Orchestrator → Specialist → Worker tree with parent-child relationships |
| **Message Bus** | Async pub/sub with topic-based routing and broadcast support |
| **Task Management** | Assign, execute, and track tasks across agents |
| **Lifecycle Hooks** | Before/after task, state change, and error hooks |
| **State Machine** | Agent states: idle, thinking, executing, waiting, completed, failed |
| **Priority Messaging** | Low, normal, high, and urgent message priorities |

---

## Installation

```bash
pip install aicp-core
```

---

## Quick Start

### Create an agent hierarchy

```python
from aicp.multi_agent import (
    AgentHierarchy,
    AgentType,
    AgentContext,
    AgentCommunicationBus,
)

# Create hierarchy
hierarchy = AgentHierarchy()

# Create agents
orchestrator = hierarchy.create_agent(
    id="orch-1",
    name="Main Orchestrator",
    agent_type=AgentType.ORCHESTRATOR,
)

specialist = hierarchy.create_agent(
    id="spec-research",
    name="Research Specialist",
    agent_type=AgentType.SPECIALIST,
    parent_id="orch-1",
    capabilities=["web.search", "web.fetch"],
)

worker = hierarchy.create_agent(
    id="worker-1",
    name="Research Worker",
    agent_type=AgentType.WORKER,
    parent_id="spec-research",
)

# Query hierarchy
children = hierarchy.get_children("orch-1")
orchestrators = hierarchy.get_orchestrators()
```

### Use the message bus

```python
bus = AgentCommunicationBus()

# Subscribe to a topic
async def on_task_update(message):
    print(f"Task update: {message.payload}")

bus.subscribe("task.update", on_task_update)

# Publish message
await bus.broadcast(
    topic="task.update",
    payload={"task_id": "abc123", "status": "completed"},
    sender_id="orch-1",
)

# Send to specific agent
await bus.send_to(
    receiver_id="spec-research",
    topic="task.assign",
    payload={"capability": "web.search", "query": "latest news"},
    sender_id="orch-1",
)
```

### Register lifecycle hooks

```python
from aicp.multi_agent import HookEvent, HookResult

async def audit_hook(task, context):
    """Log all task executions."""
    print(f"Executing: {task.capability_name} for {context.session_id}")
    return HookResult(allowed=True)

async def policy_hook(task, context):
    """Deny tasks for untrusted sessions."""
    if context.org_id is None:
        return HookResult(allowed=False, error="Untrusted session")
    return HookResult(allowed=True)

hierarchy.hooks.register(HookEvent.BEFORE_TASK, audit_hook)
hierarchy.hooks.register(HookEvent.BEFORE_TASK, policy_hook)
```

### Execute tasks

```python
from aicp.multi_agent import AgentContext

context = AgentContext(
    session_id="sess-123",
    principal_id="user-456",
    org_id="org-789",
)

# Assign task
task = await hierarchy.assign_task(
    capability_name="web.search",
    arguments={"query": "AI news"},
    context=context,
    assignee_id="spec-research",
)

# Execute with executor
async def my_executor(cap_name, args):
    return {"results": ["result1", "result2"]}

result = await hierarchy.execute_task(task.id, my_executor)
print(result.status)  # completed
print(result.result)  # {"results": [...]}
```

---

## Architecture

### Agent Types

```
Orchestrator
├── Specialist (Research)
│   ├── Worker (Search)
│   └── Worker (Fetch)
├── Specialist (Code)
│   ├── Worker (Read)
│   └── Worker (Write)
└── Specialist (Ops)
    └── Worker (Deploy)
```

### Message Flow

```
Agent A ──publish──> Bus ──dispatch──> Subscriber 1
                                      ──dispatch──> Subscriber 2
                                      ──dispatch──> Subscriber 3
```

### Hook Pipeline

```
Task Assigned → BEFORE_TASK hooks → Execute → AFTER_TASK hooks → Result
                    ↓                                      ↓
               (deny/allow)                          (transform)
                    ↓                                      ↓
              ON_ERROR hooks                       ON_STATE_CHANGE hooks
```

---

## API Reference

### AgentHierarchy

| Method | Description |
|--------|-------------|
| `create_agent(id, name, agent_type, parent_id, capabilities)` | Create agent in hierarchy |
| `get_agent(agent_id)` | Get agent by ID |
| `get_children(agent_id)` | Get child agents |
| `get_orchestrators()` | Get all orchestrator agents |
| `get_specialists()` | Get all specialist agents |
| `get_workers()` | Get all worker agents |
| `assign_task(capability_name, arguments, context, assignee_id)` | Assign task to agent |
| `execute_task(task_id, executor)` | Execute task with provided executor |
| `update_state(agent_id, state)` | Update agent state |
| `get_task(task_id)` | Get task by ID |
| `get_tasks_for_agent(agent_id)` | Get all tasks for an agent |
| `get_pending_tasks()` | Get all pending tasks |
| `get_active_tasks()` | Get all active (non-terminal) tasks |

### AgentCommunicationBus

| Method | Description |
|--------|-------------|
| `subscribe(topic, callback)` | Subscribe to a topic |
| `unsubscribe(topic, callback)` | Unsubscribe from a topic |
| `publish(message)` | Publish a message |
| `broadcast(topic, payload, sender_id)` | Broadcast to all subscribers |
| `send_to(receiver_id, topic, payload, sender_id)` | Send to specific agent |
| `start_dispatcher()` | Start background message dispatcher |
| `stop_dispatcher()` | Stop background dispatcher |

### AgentHooks

| Method | Description |
|--------|-------------|
| `register(event, hook)` | Register a hook for an event |
| `unregister(event, hook)` | Unregister a hook |
| `trigger(event, task, context)` | Trigger all hooks for an event |

---

## Hook Events

| Event | When Triggered | Use Case |
|-------|----------------|----------|
| `BEFORE_TASK` | Before task execution | Policy check, audit logging |
| `AFTER_TASK` | After task completion | Result transformation, logging |
| `BEFORE_THINK` | Before agent thinking | Context enrichment |
| `AFTER_THINK` | After agent thinking | Plan validation |
| `BEFORE_EXECUTE` | Before capability execution | Permission check |
| `AFTER_EXECUTE` | After capability execution | Result validation |
| `ON_ERROR` | On task failure | Error recovery, notification |
| `ON_STATE_CHANGE` | When agent state changes | State tracking, metrics |

---

## Package Layout

| Module | Purpose |
|--------|---------|
| `hierarchy.py` | Agent hierarchy, task management, hook system |
| `__init__.py` | Public API exports |

---

## Development

```bash
# Install for development
git clone https://github.com/aicp-ai/aicp.git
cd aicp/modules/aicp-core
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check .
```

---

## License

Apache 2.0. See `LICENSE`.
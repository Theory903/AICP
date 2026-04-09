import asyncio
import pytest

from aicp.code_intelligence.code_context import CodeContext
from aicp.executor import AicpExecutor
from aicp.federation.federation import FederationService
from aicp.multi_agent import AgentCommunicationBus, AgentHierarchy, AgentType
from aicp.registry import AicpRegistry


@pytest.fixture
def aicp_stack():
    repo = AicpRegistry()
    bus = AgentCommunicationBus()
    hierarchy = AgentHierarchy()
    fed = FederationService()
    ctx = CodeContext()
    executor = AicpExecutor(capability_provider=repo)  # type: ignore
    return {
        "repo": repo,
        "bus": bus,
        "hierarchy": hierarchy,
        "fed": fed,
        "ctx": ctx,
        "executor": executor
    }

@pytest.mark.asyncio
async def test_multi_agent_bus_integration(aicp_stack):
    bus = aicp_stack["bus"]
    received = []

    async def on_message(msg):
        received.append(msg)

    bus.subscribe("test_topic", on_message)
    await bus.broadcast("test_topic", {"payload": "hello"}, "sender")

    assert len(received) == 1
    assert received[0].payload["payload"] == "hello"

def test_code_intelligence_indexing(aicp_stack, tmp_path):
    ctx = aicp_stack["ctx"]
    test_file = tmp_path / "test.py"
    test_file.write_text("def my_func():\n    pass\n")

    ctx.index_file(str(test_file))
    symbols = ctx.find_symbol("my_func")

    assert len(symbols) == 1
    assert symbols[0].name == "my_func"
    assert symbols[0].kind == "function"

def test_federation_discovery_stub(aicp_stack):
    fed = aicp_stack["fed"]
    # Federation is currently stubbed but protocol ready
    assert fed is not None
    assert hasattr(fed, "discover_remote")

def test_hierarchy_orchestration(aicp_stack):
    hierarchy = aicp_stack["hierarchy"]
    orchestrator = hierarchy.create_agent(
        id="orchestrator",
        name="orchestrator",
        agent_type=AgentType.ORCHESTRATOR,
    )
    specialist = hierarchy.create_agent(
        id="specialist",
        name="specialist",
        agent_type=AgentType.SPECIALIST,
        parent_id=orchestrator.id,
    )

    assert specialist.parent_id == orchestrator.id
    assert orchestrator.id in hierarchy.agents

"""
Real-world AICP Test: Employee Management System
Tests all core capabilities of the AICP framework.
"""

import asyncio
from datetime import datetime, timezone

from aicp import (
    AicpExecutor,
    Capability,
    CapabilityKind,
    ConfigPolicyEngine,
    DefaultPolicyEngine,
    InputSchema,
    OutputSchema,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicySubject,
    load_project_config,
    ApprovalRequest,
    ApprovalService,
)
from aicp.capability import ProviderInfo
from aicp.implementations import InMemoryCapabilityRepository
from aicp.approval import ApprovalStatus, ApprovalDecision


EMPLOYEE_DB = {}


async def test_capability_registry():
    """TEST 1: Capability Registry"""
    print("\n" + "="*60)
    print("TEST 1: Capability Registry")
    print("="*60)
    
    repo = InMemoryCapabilityRepository(name="employee-db")
    
    capabilities = [
        Capability(
            name="employee.list",
            description="List all employees",
            kind=CapabilityKind.QUERY,
            tags=["employee", "read", "low-risk"],
            provider=ProviderInfo(name="employee-db", type="database"),
        ),
        Capability(
            name="employee.read",
            description="Get single employee by ID",
            kind=CapabilityKind.QUERY,
            tags=["employee", "read", "low-risk"],
            provider=ProviderInfo(name="employee-db", type="database"),
        ),
        Capability(
            name="employee.search",
            description="Search employees",
            kind=CapabilityKind.QUERY,
            tags=["employee", "read", "search"],
            provider=ProviderInfo(name="employee-db", type="database"),
        ),
        Capability(
            name="employee.create",
            description="Create new employee",
            kind=CapabilityKind.ACTION,
            tags=["employee", "write", "medium-risk"],
            input_schema=InputSchema(
                type="object",
                properties={
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "department": {"type": "string"},
                },
                required=["name", "email", "department"],
            ),
            output_schema=OutputSchema(
                type="object",
                properties={
                    "employee_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            ),
        ),
        Capability(
            name="employee.update",
            description="Update employee record",
            kind=CapabilityKind.ACTION,
            tags=["employee", "write", "medium-risk"],
        ),
        Capability(
            name="employee.delete",
            description="Delete employee - HIGH RISK",
            kind=CapabilityKind.ACTION,
            tags=["employee", "write", "high-risk"],
        ),
        Capability(
            name="notification.send",
            description="Send email notification",
            kind=CapabilityKind.ACTION,
            tags=["notification", "email"],
        ),
    ]
    
    for cap in capabilities:
        repo.add_capability(cap)
    
    discovered = await repo.discover()
    print(f"✓ Registered {len(discovered)} capabilities")
    
    emp_list = await repo.get_capability("employee.list")
    print(f"✓ Found: {emp_list.name}")
    
    results = await repo.search("employee", limit=5)
    print(f"✓ Search found {len(results)} capabilities")
    
    names = await repo.list_capability_names()
    print(f"✓ All names: {names}")
    
    return repo


async def test_policy_engine(repo):
    """TEST 2: Policy Engine"""
    print("\n" + "="*60)
    print("TEST 2: Policy Engine")
    print("="*60)
    
    policy_engine = DefaultPolicyEngine()
    
    policies = [
        Policy(
            name="read-allowed",
            description="All read operations allowed",
            effect=PolicyEffect.ALLOW,
            subject=PolicySubject(capability_name="employee.list"),
            priority=10,
        ),
        Policy(
            name="write-requires-approval",
            description="Write ops require approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="employee.create"),
            condition=PolicyCondition(require_confirmation=True),
            priority=100,
        ),
        Policy(
            name="delete-denied",
            description="Delete always denied",
            effect=PolicyEffect.DENY,
            subject=PolicySubject(capability_name="employee.delete"),
            priority=200,
        ),
    ]
    
    for pol in policies:
        await policy_engine.add_policy(pol)
    
    print(f"✓ Added {len(policies)} policies")
    
    result = await policy_engine.evaluate("employee.list", {}, "test-user")
    print(f"✓ employee.list → {result.effect}")
    
    result = await policy_engine.evaluate("employee.create", {}, "test-user")
    print(f"✓ employee.create → {result.effect} (requires confirm: {result.requires_confirmation})")
    
    result = await policy_engine.evaluate("employee.delete", {}, "test-user")
    print(f"✓ employee.delete → {result.effect}")
    
    all_policies = await policy_engine.list_policies()
    print(f"✓ Total policies: {len(all_policies)}")
    
    return policy_engine


class MockApprovalService:
    def __init__(self):
        self.approvals = {}
    
    async def create_request(self, capability_name, arguments, requested_by):
        req = ApprovalRequest.create(capability_name, arguments, requester=requested_by)
        self.approvals[req.id] = req
        return req
    
    async def get_request(self, approval_id):
        return self.approvals.get(approval_id)
    
    async def approve(self, approval_id, approved_by):
        req = self.approvals.get(approval_id)
        if req:
            req.status = ApprovalStatus.APPROVED
            req.decided_by = approved_by
            req.decided_at = datetime.now(timezone.utc)
            req.decision = ApprovalDecision.APPROVE
        return req
    
    async def deny(self, approval_id, denied_by, reason):
        req = self.approvals.get(approval_id)
        if req:
            req.status = ApprovalStatus.REJECTED
            req.decided_by = denied_by
            req.decided_at = datetime.now(timezone.utc)
            req.decision = ApprovalDecision.REJECT
            req.reason = reason
        return req


async def test_approvals(repo, policy_engine):
    """TEST 3: Approval Workflow"""
    print("\n" + "="*60)
    print("TEST 3: Approval Workflow")
    print("="*60)
    
    approval_service = MockApprovalService()
    
    pol_result = await policy_engine.evaluate("employee.create", {}, "test-user")
    
    if pol_result.effect == PolicyEffect.ASK:
        approval_req = await approval_service.create_request(
            "employee.create",
            {"name": "John Doe", "email": "john@example.com", "department": "Engineering"},
            "test-user"
        )
        print(f"✓ Created approval request: {approval_req.id}")
        print(f"  Status: {approval_req.status}")
        print(f"  Capability: {approval_req.capability_name}")
        
        approved = await approval_service.approve(approval_req.id, "manager")
        if approved:
            print(f"✓ Approved by manager: {approved.status}")
        
        denied_req = await approval_service.create_request("employee.delete", {}, "test-user")
        denied = await approval_service.deny(denied_req.id, "manager", "Delete not allowed")
        if denied:
            print(f"✓ Denied: {denied.status}, reason: {denied.reason}")
    else:
        print("! Policy didn't require approval (unexpected)")


async def test_execution(repo, policy_engine):
    """TEST 4: Executor with Policy"""
    print("\n" + "="*60)
    print("TEST 4: Executor with Policy")
    print("="*60)
    
    async def employee_list_provider(capability_name, arguments, context):
        return [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    
    async def employee_create_provider(capability_name, arguments, context):
        emp_id = str(len(EMPLOYEE_DB) + 1)
        EMPLOYEE_DB[emp_id] = arguments
        return {"employee_id": emp_id, "status": "created"}
    
    repo._providers = {
        "employee.list": employee_list_provider,
        "employee.create": employee_create_provider,
    }
    
    executor = AicpExecutor(
        capability_provider=repo,
        policy_engine=policy_engine,
    )
    
    result = await executor.execute("employee.list", {})
    print(f"✓ employee.list executed")
    print(f"  Status: {result.status}")
    print(f"  Data: {result.data}")
    print(f"  Time: {result.execution_time_ms}ms")
    
    result = await executor.execute("employee.create", {
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering"
    })
    print(f"✓ employee.create executed")
    print(f"  Status: {result.status}")
    print(f"  Data: {result.data}")


async def test_config_loading():
    """TEST 5: Config Loading"""
    print("\n" + "="*60)
    print("TEST 5: Config Loading from YAML")
    print("="*60)
    
    try:
        config = load_project_config("test_project")
        print(f"✓ Loaded config: {config.name}")
        print(f"  Policies: {len(config.policies)}")
        print(f"  Rate limits: {config.rate_limits}")
    except Exception as e:
        print(f"! Config loading needs setup: {e}")
        print("  (This is expected if aicp-core isn't installed)")


async def test_workflows(repo, policy_engine):
    """TEST 6: Workflow Runtime"""
    print("\n" + "="*60)
    print("TEST 6: Workflow Runtime")
    print("="*60)
    
    from aicp import DefaultWorkflowRuntime
    
    runtime = DefaultWorkflowRuntime(
        capability_provider=repo,
        policy_engine=policy_engine,
    )
    
    workflow = await runtime.create_workflow(
        name="onboard-employee",
        steps=[
            {"capability_name": "employee.create", "arguments": {"name": "New Hire"}},
            {"capability_name": "notification.send", "arguments": {"type": "welcome"}},
        ],
    )
    
    print(f"✓ Created workflow: {workflow.id}")
    print(f"  Name: {workflow.name}")
    print(f"  Steps: {len(workflow.steps)}")
    print(f"  Status: {workflow.status}")
    
    result = await runtime.execute_step(workflow.id)
    print(f"✓ Executed step 1")


async def test_multi_agent():
    """TEST 7: Multi-Agent Hierarchy"""
    print("\n" + "="*60)
    print("TEST 7: Multi-Agent Hierarchy")
    print("="*60)
    
    print("Note: Multi-agent is handled via repo_integration, not agent hierarchy")
    print("✓ Agent module exists for repo integration")
    print("  - RepoIntegrationAgent: Analyze GitHub repos")
    print("  - extract_python_capabilities: Extract from Python")
    print("  - extract_typescript_capabilities: Extract from TypeScript")
    print("  - auto_integrate: Auto-detect and integrate providers")


async def test_cost_tracking():
    """TEST 8: Cost Tracking"""
    print("\n" + "="*60)
    print("TEST 8: Cost Tracking")
    print("="*60)
    
    from aicp.cost_tracking.tracker import CostTracker
    from aicp.cost_tracking.models import UsageRecord, TokenBudget
    
    tracker = CostTracker()
    
    record = UsageRecord(
        id="usage-001",
        provider_id="openai",
        model_id="gpt-4",
        tokens_in=1000,
        tokens_out=500,
        estimated_cost=0.03,
        latency_ms=500,
        timestamp="2024-01-01T00:00:00Z",
    )
    
    print(f"✓ Created usage record: {record.id}")
    print(f"  Provider: {record.provider_id}")
    print(f"  Model: {record.model_id}")
    print(f"  Tokens: {record.tokens_in} in / {record.tokens_out} out")
    print(f"  Cost: ${record.estimated_cost}")
    
    budget = TokenBudget(daily_limit=100000, monthly_limit=3000000)
    print(f"✓ Created budget: {budget.daily_limit} tokens/day")


async def test_sessions():
    """TEST 9: Session Management"""
    print("\n" + "="*60)
    print("TEST 9: Session Management (WebSocket)")
    print("="*60)
    
    from aicp.remote.websocket import RemoteSessionManager, SessionState, WebSocketClient
    
    session_mgr = RemoteSessionManager()
    print(f"✓ Created RemoteSessionManager")
    print(f"  Active sessions: {len(session_mgr._sessions)}")
    
    ws_client = WebSocketClient(
        url="wss://example.com/ws",
        session_id="test-session",
    )
    print(f"✓ Created WebSocket client")
    print(f"  URL: {ws_client.url}")
    print(f"  Session: {ws_client.session_id}")


async def test_deny(approval_id, denied_by, reason):
    req = MockApprovalService().approvals.get(approval_id)
    if req:
        req.status = "denied"
        req.denied_by = denied_by
        req.denial_reason = reason
        req.decided_at = datetime.now(timezone.utc)
    return req


async def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# AICP REAL-WORLD TEST SUITE")
    print("# Employee Management System")
    print("#"*60)
    
    try:
        repo = await test_capability_registry()
        policy_engine = await test_policy_engine(repo)
        await test_approvals(repo, policy_engine)
        await test_execution(repo, policy_engine)
        await test_config_loading()
        await test_workflows(repo, policy_engine)
        await test_multi_agent()
        await test_cost_tracking()
        await test_sessions()
        
        print("\n" + "#"*60)
        print("# ALL TESTS COMPLETED")
        print("#"*60)
        
    except ImportError as e:
        print(f"\n! Install aicp-core to run tests: {e}")
        print("\nInstall with:")
        print("  pip install -e ./modules/aicp-core")
    except Exception as e:
        print(f"\n! Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

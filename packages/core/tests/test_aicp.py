"""Tests for AICP core implementations."""

from datetime import datetime
from typing import Any, cast

import pytest

from aicp import AicpExecutor, Capability, CapabilityKind, InputSchema, OutputSchema
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.policy_engine import Policy, PolicyCondition, PolicyEffect, PolicySubject


@pytest.fixture
def repo():
    """Create a test repository."""
    return InMemoryCapabilityRepository("test")


@pytest.fixture
def policy_engine():
    """Create a test policy engine."""
    return DefaultPolicyEngine()


@pytest.fixture
def workflow_runtime(repo, policy_engine):
    """Create a test workflow runtime."""
    return DefaultWorkflowRuntime(repo, policy_engine)


def _noop_handler(args, ctx):
    """Default test handler that echoes arguments."""
    return {"executed": True, **args}


@pytest.fixture
def sample_capability():
    """Create a sample capability."""
    return Capability(
        name="payments.transfer",
        description="Transfer funds",
        kind=CapabilityKind.ACTION,
    )


class TestCapabilityRepository:
    async def test_add_and_get_capability(self, repo, sample_capability):
        repo.add_capability(sample_capability)
        result = await repo.get_capability("payments.transfer")
        assert result is not None
        assert result.name == "payments.transfer"

    async def test_discover_capabilities(self, repo, sample_capability):
        repo.add_capability(sample_capability)
        capabilities = await repo.discover()
        assert len(capabilities) == 1

    async def test_remove_capability(self, repo, sample_capability):
        repo.add_capability(sample_capability)
        removed = repo.remove_capability("payments.transfer")
        assert removed is True
        result = await repo.get_capability("payments.transfer")
        assert result is None


class TestPolicyEngine:
    async def test_allow_by_default(self, policy_engine):
        decision = await policy_engine.evaluate(
            "payments.transfer",
            {"amount": 100},
        )
        assert decision.effect == PolicyEffect.ALLOW

    async def test_deny_policy(self, policy_engine):
        policy = Policy(
            name="deny_payments",
            effect=PolicyEffect.DENY,
            subject=PolicySubject(capability_name="payments.transfer"),
        )
        await policy_engine.add_policy(policy)

        decision = await policy_engine.evaluate(
            "payments.transfer",
            {"amount": 100},
        )
        assert decision.effect == PolicyEffect.DENY


class TestWorkflowRuntime:
    async def test_create_workflow(self, workflow_runtime):
        workflow = await workflow_runtime.create_workflow(
            name="transfer_funds",
            description="Transfer funds between accounts",
            steps=[
                {"capability_name": "payments.validate", "arguments": {}},
                {"capability_name": "payments.transfer", "arguments": {}},
            ],
        )
        assert workflow.name == "transfer_funds"
        assert len(workflow.steps) == 2
        assert workflow.status == "pending"
        assert datetime.fromisoformat(workflow.created_at.replace("Z", "+00:00"))
        assert datetime.fromisoformat(workflow.updated_at.replace("Z", "+00:00"))

    async def test_execute_workflow_with_confirmation(self, workflow_runtime, sample_capability):
        workflow_runtime._provider.add_capability(sample_capability, handler=_noop_handler)

        policy = Policy(
            name="require_confirmation",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
        await workflow_runtime._policy_engine.add_policy(policy)

        workflow = await workflow_runtime.create_workflow(
            name="transfer",
            steps=[{"capability_name": "payments.transfer", "arguments": {"amount": 100}}],
        )

        result = await workflow_runtime.execute_step(workflow.id)
        assert result.requires_confirmation is True
        workflow = await workflow_runtime.get_workflow(workflow.id)
        assert workflow is not None
        assert workflow.status == "paused"
        assert datetime.fromisoformat(workflow.updated_at.replace("Z", "+00:00"))

    async def test_workflow_completion(self, workflow_runtime, sample_capability):
        workflow_runtime._provider.add_capability(sample_capability, handler=_noop_handler)

        workflow = await workflow_runtime.create_workflow(
            name="simple",
            steps=[{"capability_name": "payments.transfer", "arguments": {}}],
        )

        result = await workflow_runtime.execute_step(workflow.id)
        assert result.success is True
        assert result.next is not None
        assert result.next.get("action") == "complete"
        workflow = await workflow_runtime.get_workflow(workflow.id)
        assert workflow is not None
        assert workflow.status == "completed"
        assert datetime.fromisoformat(workflow.updated_at.replace("Z", "+00:00"))


class TestCapabilityValidation:
    """Tests for capability schema structures."""

    def test_capability_with_complex_input_schema(self):
        """Test capability with complex input schema structure."""
        cap = Capability(
            name="user.create",
            description="Create a user",
            kind=CapabilityKind.ACTION,
            input_schema=InputSchema(
                properties={
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 18},
                },
                required=["email"],
            ),
        )

        assert cap.name == "user.create"
        assert "email" in cap.input_schema.properties
        assert "age" in cap.input_schema.properties
        assert "email" in cap.input_schema.required

    def test_capability_with_nested_output_schema(self):
        """Test capability with nested output schema."""
        cap = Capability(
            name="payment.process",
            description="Process payment",
            kind=CapabilityKind.ACTION,
            output_schema=OutputSchema(
                properties={
                    "transaction": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "amount": {"type": "number"},
                        },
                    },
                    "status": {"type": "string"},
                },
            ),
        )

        assert "transaction" in cap.output_schema.properties
        assert cap.output_schema.properties["transaction"]["type"] == "object"


class TestErrorHandling:
    """Tests for error handling."""

    def test_executor_returns_not_found(self):
        """Test executor returns proper not found result."""
        from aicp.interfaces import ExecutionStatus

        repo = InMemoryCapabilityRepository()
        executor = AicpExecutor(repo, DefaultPolicyEngine())

        import asyncio

        async def run():
            result = await executor.execute("nonexistent.capability", {})
            return result

        result = asyncio.run(run())
        assert result.status == ExecutionStatus.FAILURE
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_executor_returns_requires_approval_with_dict_based_approval_service(self):
        from aicp.interfaces import ExecutionStatus

        repo = InMemoryCapabilityRepository()
        repo.add_capability(
            Capability(
                name="students.create",
                description="Create student",
                kind=CapabilityKind.ACTION,
            ),
            handler=_noop_handler,
        )
        executor = AicpExecutor(repo, DefaultPolicyEngine())

        class DictApprovalService:
            async def create_approval_request(self, **kwargs):
                return {"id": "apr_123", **kwargs}

        cast(Any, executor)._approval_service = DictApprovalService()

        policy = Policy(
            name="require_approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="students.create"),
            condition=PolicyCondition(require_confirmation=True),
        )

        import asyncio

        async def run():
            policy_engine = cast(Any, executor._policy_engine)
            await policy_engine.add_policy(policy)
            return await executor.execute(
                "students.create",
                {"body": {"name": "Abhi"}},
                {"requester_id": "cli-user"},
            )

        result = asyncio.run(run())

        assert result.status == ExecutionStatus.FAILURE
        assert result.error_code == "requires_approval"
        assert result.approval_request_id == "apr_123"

    def test_execute_after_approval_bypasses_policy_re_evaluation(self):
        from aicp.interfaces import ExecutionStatus

        repo = InMemoryCapabilityRepository()
        repo.add_capability(
            Capability(
                name="students.create",
                description="Create student",
                kind=CapabilityKind.ACTION,
            ),
            handler=_noop_handler,
        )
        executor = AicpExecutor(repo, DefaultPolicyEngine())

        class DictApprovalService:
            async def get_request(self, request_id):
                return {
                    "id": request_id,
                    "capability_name": "students.create",
                    "arguments": {"body": {"name": "Abhi"}},
                    "status": "approved",
                    "decided_by": "manager-1",
                    "decided_at": "2026-04-01T00:00:00+00:00",
                }

        cast(Any, executor)._approval_service = DictApprovalService()

        policy = Policy(
            name="require_approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="students.create"),
            condition=PolicyCondition(require_confirmation=True),
        )

        import asyncio

        async def run():
            policy_engine = cast(Any, executor._policy_engine)
            await policy_engine.add_policy(policy)
            return await executor.execute_after_approval("apr_123")

        result = asyncio.run(run())

        assert result.status == ExecutionStatus.SUCCESS
        assert result.data["executed"] is True

    def test_executor_fails_when_output_validation_mode_is_strict(self):
        from aicp.interfaces import ExecutionStatus

        repo = InMemoryCapabilityRepository()
        repo.add_capability(
            Capability(
                name="students.get",
                description="Get student",
                kind=CapabilityKind.QUERY,
                output_schema=OutputSchema(
                    type="object",
                    properties={"id": {"type": "string"}},
                    required=["id"],
                ),
                output_validation_mode="strict",
            ),
            handler=lambda args, ctx: {"name": "Abhi"},
        )
        executor = AicpExecutor(repo, DefaultPolicyEngine())

        import asyncio

        result = asyncio.run(executor.execute("students.get", {}))

        assert result.status == ExecutionStatus.FAILURE
        assert result.error_code == "output_validation_failed"
        assert result.error is not None
        assert "output schema" in result.error.lower()

    def test_executor_warns_when_output_validation_mode_is_warn(self):
        from aicp.interfaces import ExecutionStatus

        repo = InMemoryCapabilityRepository()
        repo.add_capability(
            Capability(
                name="students.get",
                description="Get student",
                kind=CapabilityKind.QUERY,
                output_schema=OutputSchema(
                    type="object",
                    properties={"id": {"type": "string"}},
                    required=["id"],
                ),
                output_validation_mode="warn",
            ),
            handler=lambda args, ctx: {"name": "Abhi"},
        )
        executor = AicpExecutor(repo, DefaultPolicyEngine())

        import asyncio

        result = asyncio.run(executor.execute("students.get", {}))

        assert result.status == ExecutionStatus.SUCCESS
        assert result.warnings is not None
        assert result.warnings[0]["code"] == "output_validation_warning"


class TestPolicyConditions:
    """Tests for policy conditions."""

    async def test_policy_with_confirmation_ask(self, policy_engine):
        """Test policy that requires confirmation."""
        policy = Policy(
            name="require_confirmation",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
        await policy_engine.add_policy(policy)

        decision = await policy_engine.evaluate("payments.transfer", {"amount": 100}, {})
        assert decision.effect == PolicyEffect.ASK
        assert "require_confirmation" in decision.reason.lower()

    async def test_policy_with_rate_limit(self, policy_engine):
        """Test policy with rate limiting."""
        policy = Policy(
            name="rate_limit",
            effect=PolicyEffect.LIMIT,
            subject=PolicySubject(capability_name="api.request"),
            condition=PolicyCondition(max_rate_per_minute=100),
        )
        await policy_engine.add_policy(policy)

        decision = await policy_engine.evaluate("api.request", {}, {})
        assert decision.effect == PolicyEffect.LIMIT

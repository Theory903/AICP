"""Runtime-backed flagship payment transfer demo."""

from pathlib import Path
from typing import Any

from aicp import Policy, PolicyCondition, PolicyEffect, PolicySubject
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.services import ApprovalService, AuditService, WorkflowService

from payment_transfer.capabilities import create_payment_capabilities

APPROVAL_THRESHOLD = 1000.0


def _as_json(value: Any) -> Any:
    """Serialize pydantic models without constraining callers to one concrete type."""
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return value


async def run_platform_demo(store_path: str | Path, amount: float = 2000.0) -> dict:
    """Run an end-to-end governed transfer over the runtime stack.

    Args:
        store_path: Path for the runtime store
        amount: Transfer amount (default: 2000, triggers approval)
                 Use < 1000 to skip approval
    """
    runtime_store = FileRuntimeStore(store_path)
    capability_provider = InMemoryCapabilityRepository("payment-demo")
    for capability in create_payment_capabilities():
        capability_provider.add_capability(capability)

    policy_engine = DefaultPolicyEngine()
    if amount > APPROVAL_THRESHOLD:
        await policy_engine.add_policy(
            Policy(
                name="high_value_approval",
                description=f"Transfers over ${APPROVAL_THRESHOLD} require approval",
                effect=PolicyEffect.ASK,
                subject=PolicySubject(capability_name="payments.transfer"),
                condition=PolicyCondition(require_confirmation=True),
            )
        )

    audit_service = AuditService(runtime_store)
    approval_service = ApprovalService(runtime_store, audit_service=audit_service)
    workflow_service = WorkflowService(
        capability_provider=capability_provider,
        runtime_store=runtime_store,
        policy_engine=policy_engine,
        approval_service=approval_service,
        audit_service=audit_service,
    )

    workflow = await workflow_service.create_workflow(
        name="payment_transfer_demo",
        description="Governed high-value transfer demo",
        steps=[
            {
                "capability_name": "payments.transfer",
                "arguments": {
                    "from_account": "user123",
                    "to_account": "merchant456",
                    "amount": amount,
                },
            }
        ],
    )

    initial_result = await workflow_service.execute_step(
        workflow.id,
        {"requester": "agent-demo"},
    )

    approvals = await approval_service.list_approvals()
    approval = None
    resumed_result = None

    if approvals:
        approval = approvals[0]
        resumed_result = await workflow_service.resume_after_approval(
            workflow.id,
            approval_id=approval["id"],
            decision="approved",
            approver="manager-demo",
        )
        approval = await approval_service.get_approval(approval["id"])
        approvals = [approval] if approval is not None else []

    final_workflow = await workflow_service.get_workflow(workflow.id)
    history = await audit_service.list_entries(workflow_id=workflow.id)

    return {
        "workflow": _as_json(final_workflow) if final_workflow else None,
        "approval": _as_json(approval) if approval else None,
        "approval_requests": [_as_json(a) for a in approvals],
        "execution_result": _as_json(resumed_result or initial_result),
        "history": history,
    }


async def main() -> None:
    summary = await run_platform_demo("./.aicp-payment-demo")
    print("AICP Platform Demo")
    print("Workflow:", summary["workflow"]["id"], summary["workflow"]["status"])
    print("Approval:", summary["approval"]["id"], summary["approval"]["status"])
    print("History entries:", len(summary["history"]))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

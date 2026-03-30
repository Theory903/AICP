"""Runtime-backed flagship payment transfer demo."""

from pathlib import Path

from aicp import Policy, PolicyCondition, PolicyEffect, PolicySubject
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.services import ApprovalService, AuditService, WorkflowService

from payment_transfer.capabilities import create_payment_capabilities

APPROVAL_THRESHOLD = 1000.0


async def run_platform_demo(store_path: str | Path) -> dict:
    """Run an end-to-end governed transfer over the runtime stack."""
    runtime_store = FileRuntimeStore(store_path)
    capability_provider = InMemoryCapabilityRepository("payment-demo")
    for capability in create_payment_capabilities():
        capability_provider.add_capability(capability)

    policy_engine = DefaultPolicyEngine()
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
                    "amount": 2000.00,
                },
            }
        ],
    )

    paused_result = await workflow_service.execute_step(workflow.id, {"requester": "agent-demo"})
    approval = (await approval_service.list_approvals())[0]
    resumed_result = await workflow_service.resume_after_approval(
        workflow.id,
        approval_id=approval["id"],
        decision="approved",
        approver="manager-demo",
    )

    final_workflow = await workflow_service.get_workflow(workflow.id)
    final_approval = await approval_service.get_approval(approval["id"])
    history = await audit_service.list_entries(workflow_id=workflow.id)

    return {
        "workflow": final_workflow.model_dump(mode="json") if final_workflow else None,
        "approval": final_approval,
        "execution_result": resumed_result.model_dump(mode="json"),
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

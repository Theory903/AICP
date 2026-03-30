"""Approval service for runtime-native HITL flows."""

import uuid
from typing import Any

from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.audit import AuditService


class ApprovalService:
    """Manage approval requests and decisions."""

    def __init__(self, runtime_store: RuntimeStore, audit_service: AuditService | None = None):
        self._store = runtime_store
        self._audit = audit_service

    async def create_approval_request(
        self,
        capability_name: str,
        workflow_id: str,
        arguments: dict[str, Any],
        requester: str,
        message: str,
        step_id: str | None = None,
        policy_name: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now_rfc3339()
        request = {
            "id": f"apr_{uuid.uuid4().hex[:8]}",
            "capability_name": capability_name,
            "arguments": arguments,
            "requester": requester,
            "requested_at": now,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "policy_matched": policy_name,
            "message": message,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        await self._store.save_approval_request(request)
        if self._audit is not None:
            await self._audit.append(
                event_type="approval_request_created",
                actor=requester,
                capability_name=capability_name,
                workflow_id=workflow_id,
                step_id=step_id,
                approval_request_id=request["id"],
                status="pending",
                metadata={"message": message, "policy_name": policy_name},
            )
        return request

    async def list_approvals(self) -> list[dict[str, Any]]:
        return await self._store.list_approval_requests()

    async def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        return await self._store.get_approval_request(approval_id)

    async def decide(
        self,
        approval_id: str,
        decision: str,
        approver: str,
        reason: str | None = None,
        modified_arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = await self._store.get_approval_request(approval_id)
        if request is None:
            raise ValueError(f"Approval request not found: {approval_id}")

        now = utc_now_rfc3339()
        record = {
            "id": f"dec_{uuid.uuid4().hex[:8]}",
            "request_id": approval_id,
            "decision": decision,
            "approver": approver,
            "reason": reason,
            "modified_arguments": modified_arguments,
            "decided_at": now,
            "received_at": request["requested_at"],
        }
        await self._store.save_approval_decision(record)

        request["status"] = decision
        request["updated_at"] = now
        await self._store.save_approval_request(request)

        if self._audit is not None:
            await self._audit.append(
                event_type="approval_decision_made",
                actor=approver,
                capability_name=request["capability_name"],
                workflow_id=request.get("workflow_id"),
                step_id=request.get("step_id"),
                approval_request_id=approval_id,
                approval_decision_id=record["id"],
                status="success",
                metadata={"decision": decision, "reason": reason},
            )
        return record

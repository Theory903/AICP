"""Approval service for runtime-native HITL flows."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.audit import AuditService

_ALLOWED_DECISIONS = {"approved", "rejected"}
_PENDING_STATUS = "pending"


class ApprovalService:
    """Manage approval requests and decisions."""

    def __init__(
        self,
        runtime_store: RuntimeStore,
        audit_service: AuditService | None = None,
        capability_provider: CapabilityProvider | None = None,
    ):
        self._store = runtime_store
        self._audit = audit_service
        self._provider = capability_provider

    async def create_approval_request(
        self,
        capability_name: str,
        workflow_id: str | None,
        arguments: dict[str, Any],
        requester: Any,
        message: str | None = None,
        step_id: str | None = None,
        policy_name: str | None = None,
        execution_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new approval request."""
        now = utc_now_rfc3339()

        capability_name = self._require_text(
            capability_name, field_name="capability_name"
        )
        requester = self._normalize_requester(requester)
        message = self._require_text(message or "Approval required", field_name="message")

        request = {
            "id": f"apr_{uuid.uuid4().hex[:8]}",
            "capability_name": capability_name,
            "arguments": deepcopy(arguments or {}),
            "requester": requester,
            "requested_at": now,
            "workflow_id": self._normalize_optional_text(workflow_id),
            "step_id": self._normalize_optional_text(step_id),
            "policy_matched": self._normalize_optional_text(policy_name),
            "message": message,
            "execution_id": self._normalize_optional_text(execution_id),
            "context": deepcopy(context or {}),
            "status": _PENDING_STATUS,
            "created_at": now,
            "updated_at": now,
        }

        await self._store.save_approval_request(request)

        if self._audit is not None:
            await self._audit.append(
                event_type="approval_request_created",
                actor=requester,
                capability_name=capability_name,
                workflow_id=request["workflow_id"],
                step_id=request["step_id"],
                approval_request_id=request["id"],
                status=_PENDING_STATUS,
                metadata={
                    "message": message,
                    "policy_name": request["policy_matched"],
                    "execution_id": request["execution_id"],
                },
            )

        return deepcopy(request)

    async def list_approvals(self) -> list[dict[str, Any]]:
        """List approval requests."""
        approvals = await self._store.list_approval_requests()
        return [deepcopy(item) for item in approvals]

    async def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        """Get one approval request by ID."""
        approval_id = self._require_text(approval_id, field_name="approval_id")
        request = await self._store.get_approval_request(approval_id)
        return deepcopy(request) if request is not None else None

    async def find_approved_for_intent(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Find an approved approval for matching intent.

        Matches by capability_name + arguments directly from approval.
        """
        try:
            approvals = await self._store.list_approval_requests()
        except Exception:
            return None

        normalized_args = self._normalize_for_matching(arguments or {})
        normalized_context = self._normalize_for_matching({
            k: v for k, v in (context or {}).items()
            if k in {"tenant_id", "user_id", "session_id"}
        })
        intent_key = f"{capability_name}:{normalized_args}:{normalized_context}"

        for approval in approvals:
            try:
                status = str(approval.get("status") or "").strip().lower()
                if status != "approved":
                    continue

                saved_args = approval.get("arguments") or {}
                saved_context = self._normalize_for_matching({
                    k: v for k, v in (approval.get("context") or {}).items()
                    if k in {"tenant_id", "user_id", "session_id"}
                })
                saved_intent = f"{capability_name}:{self._normalize_for_matching(saved_args)}:{saved_context}"
                if saved_intent == intent_key:
                    return deepcopy(approval)
            except Exception:
                continue
        return None

    @staticmethod
    def _normalize_for_matching(data: Any) -> str:
        """Normalize data for intent matching."""
        if isinstance(data, dict):
            normalized_items = sorted(
                (k, ApprovalService._normalize_for_matching(v)) for k, v in data.items()
            )
            return f"{{{','.join(f'{k}:{v}' for k, v in normalized_items)}}}"
        if isinstance(data, list):
            return f"[{','.join(ApprovalService._normalize_for_matching(item) for item in data)}]"
        if isinstance(data, str):
            return f'"{data}"'
        if isinstance(data, (int, float, bool)):
            return str(data).lower()
        if data is None:
            return "null"
        return f'"{str(data)}"'

    async def decide(
        self,
        approval_id: str,
        decision: str,
        approver: str,
        reason: str | None = None,
        modified_arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply an approval decision to a pending request."""
        approval_id = self._require_text(approval_id, field_name="approval_id")
        decision = self._normalize_decision(decision)
        approver = self._require_text(approver, field_name="approver")
        reason = self._normalize_optional_text(reason)

        request = await self._store.get_approval_request(approval_id)
        if request is None:
            raise ValueError(f"Approval request not found: {approval_id}")

        current_status = str(request.get("status", "")).strip().lower()
        if current_status != _PENDING_STATUS:
            raise ValueError(
                f"Approval request is not pending: {approval_id} (status={request.get('status')})"
            )

        now = utc_now_rfc3339()
        record = {
            "id": f"dec_{uuid.uuid4().hex[:8]}",
            "request_id": approval_id,
            "decision": decision,
            "approver": approver,
            "reason": reason,
            "modified_arguments": deepcopy(modified_arguments)
            if modified_arguments is not None
            else None,
            "decided_at": now,
            "received_at": request.get("requested_at"),
        }

        await self._store.save_approval_decision(record)

        updated_request = deepcopy(request)
        updated_request["status"] = decision
        updated_request["updated_at"] = now
        if modified_arguments is not None:
            updated_request["modified_arguments"] = deepcopy(modified_arguments)
        if reason is not None:
            updated_request["decision_reason"] = reason
        updated_request["decided_by"] = approver
        updated_request["decided_at"] = now

        await self._store.save_approval_request(updated_request)

        if self._audit is not None:
            await self._audit.append(
                event_type="approval_decision_made",
                actor=approver,
                capability_name=updated_request.get("capability_name"),
                workflow_id=updated_request.get("workflow_id"),
                step_id=updated_request.get("step_id"),
                approval_request_id=approval_id,
                approval_decision_id=record["id"],
                status=decision,
                metadata={
                    "decision": decision,
                    "reason": reason,
                },
            )

        return deepcopy(record)

    async def get_review_packet(self, approval_id: str) -> dict[str, Any] | None:
        """Build a structured operator review packet for an approval request."""
        approval = await self.get_approval(approval_id)
        if approval is None:
            return None

        capability_name = str(approval.get("capability_name") or "unknown")
        capability = (
            await self._provider.get_capability(capability_name)
            if self._provider is not None
            else None
        )
        history = (
            await self._audit.list_entries(approval_request_id=approval_id)
            if self._audit is not None
            else []
        )

        workflow_id = self._normalize_optional_text(approval.get("workflow_id"))
        execution_id = self._normalize_optional_text(approval.get("execution_id"))
        workflow = await self._store.get_workflow(workflow_id) if workflow_id else None
        execution = (
            await self._store.get_execution_record(execution_id) if execution_id else None
        )
        raw_context = approval.get("context")
        context: dict[str, Any] = raw_context if isinstance(raw_context, dict) else {}
        continuation = getattr(capability, "continuation", None)
        decision_entry = next(
            (
                entry
                for entry in reversed(history)
                if str(entry.get("event_type") or "") == "approval_decision_made"
            ),
            None,
        )

        return {
            "approval": {
                "id": str(approval.get("id") or approval_id),
                "status": str(approval.get("status") or "pending"),
                "requested_at": approval.get("requested_at") or approval.get("created_at"),
                "decided_at": approval.get("decided_at"),
                "message": approval.get("message"),
            },
            "requested_capability": {
                "name": capability_name,
                "description": getattr(capability, "description", None),
                "kind": getattr(getattr(capability, "kind", None), "value", None)
                or self._normalize_optional_text(getattr(capability, "kind", None)),
                "provider_name": self._normalize_optional_text(
                    getattr(getattr(capability, "provider", None), "name", None)
                ),
                "provider_type": self._normalize_optional_text(
                    getattr(getattr(capability, "provider", None), "type", None)
                ),
                "arguments": deepcopy(
                    approval.get("modified_arguments") or approval.get("arguments") or {}
                ),
            },
            "requester_context": {
                "requester": approval.get("requester"),
                "tenant_id": context.get("tenant_id"),
                "user_id": context.get("user_id"),
                "session_id": context.get("session_id"),
                "interaction_id": context.get("interaction_id"),
                "context": deepcopy(context),
            },
            "approver_context": {
                "approver": approval.get("decided_by")
                or (decision_entry or {}).get("actor"),
                "decision": (decision_entry or {}).get("metadata", {}).get("decision")
                or approval.get("status"),
                "reason": approval.get("decision_reason")
                or (decision_entry or {}).get("metadata", {}).get("reason"),
                "decided_at": approval.get("decided_at")
                or (decision_entry or {}).get("timestamp"),
            },
            "linkage": {
                "workflow": {
                    "id": workflow_id,
                    "name": getattr(workflow, "name", None),
                    "status": getattr(getattr(workflow, "status", None), "value", None),
                    "step_id": approval.get("step_id"),
                    "current_step_id": getattr(
                        getattr(workflow, "current_step", None), "id", None
                    ),
                    "current_step_capability": getattr(
                        getattr(workflow, "current_step", None), "capability_name", None
                    ),
                },
                "execution": {
                    "id": execution_id,
                    "status": (execution or {}).get("status") if execution else None,
                    "created_at": (execution or {}).get("created_at") if execution else None,
                },
            },
            "policy": {
                "effect": str(
                    approval.get("policy_effect") or approval.get("effect") or "ask"
                ),
                "policy_name": approval.get("policy_matched"),
                "reason": approval.get("message"),
                "required_role": approval.get("required_role")
                or approval.get("approver_role"),
            },
            "impact_summary": self._impact_summary(
                approval=approval,
                capability=capability,
                context=context,
            ),
            "implications": {
                "next_action": self._next_action(approval),
                "resume_available": bool(workflow_id),
                "next_capabilities": list(
                    getattr(continuation, "next_capabilities", []) or []
                ),
                "next_hint": getattr(continuation, "next_hint", None),
            },
            "history": [deepcopy(entry) for entry in history],
        }

    def _normalize_decision(self, decision: str) -> str:
        """Normalize and validate a decision value."""
        normalized = self._require_text(decision, field_name="decision").lower()
        if normalized not in _ALLOWED_DECISIONS:
            allowed = ", ".join(sorted(_ALLOWED_DECISIONS))
            raise ValueError(
                f"Invalid decision '{decision}'. Expected one of: {allowed}"
            )
        return normalized

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        """Require a non-empty text value."""
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        """Normalize optional text to stripped string or None."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _normalize_requester(self, requester: Any) -> str:
        """Normalize requester identity from string or approval context object."""
        if isinstance(requester, str):
            return self._require_text(requester, field_name="requester")

        for attr in ("requester_id", "requester_email", "requester_role", "tenant_id"):
            value = getattr(requester, attr, None)
            if value is not None:
                normalized = str(value).strip()
                if normalized:
                    return normalized

        return self._require_text(str(requester or "requester"), field_name="requester")

    def _next_action(self, approval: dict[str, Any]) -> str:
        """Return the most relevant operator next step for an approval."""
        status = str(approval.get("status") or "pending").strip().lower()
        workflow_id = self._normalize_optional_text(approval.get("workflow_id"))
        execution_id = self._normalize_optional_text(approval.get("execution_id"))

        if status == "pending":
            if workflow_id:
                return "Review and decide the approval to unblock workflow continuation."
            if execution_id:
                return "Review and decide the approval before execution can continue."
            return "Review the request and record an approval decision."
        if status == "approved" and workflow_id:
            return "Resume the paused workflow step with the recorded approval."
        if status == "rejected" and workflow_id:
            return "Investigate the rejected workflow step before retrying or replacing it."
        if status == "approved":
            return "Proceed with the approved action path."
        return "No further automated step is available from this approval packet."

    def _impact_summary(
        self,
        *,
        approval: dict[str, Any],
        capability: Any,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a deterministic, operator-friendly impact summary."""
        arguments = approval.get("modified_arguments") or approval.get("arguments") or {}
        arguments_dict = arguments if isinstance(arguments, dict) else {}
        rollback_capability = self._normalize_optional_text(
            getattr(capability, "rollback_capability", None)
        )
        auth_requirement = getattr(capability, "auth", None)
        capability_name = str(approval.get("capability_name") or "")

        return {
            "risk_level": self._risk_level(approval=approval, capability=capability),
            "destructive": bool(getattr(capability, "is_destructive", False)),
            "affected_resource_hints": self._affected_resource_hints(
                capability_name=capability_name,
                arguments=arguments_dict,
            ),
            "affected_capabilities": self._affected_capabilities(
                capability_name=capability_name,
                context=context,
            ),
            "data_classification": self._data_classification(capability_name),
            "compliance_flags": self._compliance_flags(capability_name),
            "time_sensitivity": self._time_sensitivity(capability_name),
            "rollback_capability": rollback_capability,
            "reversible": bool(rollback_capability),
            "blast_radius_estimate": self._blast_radius_estimate(
                capability=capability,
                arguments=arguments_dict,
                context=context,
            ),
            "auth_session_implications": self._auth_session_implications(
                auth_requirement=auth_requirement,
                context=context,
            ),
        }

    def _risk_level(self, *, approval: dict[str, Any], capability: Any) -> str:
        """Infer a coarse deterministic risk level for approval review."""
        explicit_risk = self._normalize_optional_text(getattr(capability, "risk", None))
        if explicit_risk is not None:
            return explicit_risk
        if bool(getattr(capability, "is_destructive", False)):
            return "high"

        kind = self._normalize_optional_text(
            getattr(getattr(capability, "kind", None), "value", None)
            or getattr(capability, "kind", None)
        )
        if kind in {"query"}:
            return "low"
        if str(approval.get("policy_effect") or approval.get("effect") or "ask") == "ask":
            return "medium"
        return "medium"

    def _affected_resource_hints(
        self,
        *,
        capability_name: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        """Return lightweight resource hints from capability names and identifiers."""
        hints: list[str] = []
        seen: set[str] = set()

        resource_hint = self._normalize_optional_text(capability_name.partition(".")[0])
        if resource_hint is not None:
            seen.add(resource_hint)
            hints.append(resource_hint)

        for key in arguments:
            key_text = str(key).strip()
            lowered = key_text.lower()
            if lowered == "id" or lowered.endswith("_id"):
                if key_text not in seen:
                    seen.add(key_text)
                    hints.append(key_text)

        return hints

    def _blast_radius_estimate(
        self,
        *,
        capability: Any,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Estimate the likely blast radius using deterministic heuristics."""
        capability_name = self._normalize_optional_text(getattr(capability, "name", None)) or ""
        lowered_name = capability_name.lower()
        argument_keys = {str(key).strip().lower() for key in arguments}

        if getattr(getattr(capability, "kind", None), "value", None) == "query":
            return "read_only"
        if any(token in lowered_name for token in ("bulk", "batch", "sync", "import", "export")):
            return "multi_resource"
        if "tenant_id" in argument_keys or context.get("tenant_id") is not None:
            return "tenant_scope"
        if "id" in argument_keys or any(key.endswith("_id") for key in argument_keys):
            return "single_resource"
        if bool(getattr(capability, "is_destructive", False)):
            return "multi_resource"
        return "unknown"

    def _auth_session_implications(
        self,
        *,
        auth_requirement: Any,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Summarize auth/session coupling when relevant to the approval."""
        if auth_requirement is None:
            return None

        requires_session = bool(getattr(auth_requirement, "requires_session", False))
        auth_mode = self._normalize_optional_text(getattr(auth_requirement, "mode", None))
        required_session_provider = self._normalize_optional_text(
            getattr(auth_requirement, "required_session_provider", None)
        )
        refreshable = bool(getattr(auth_requirement, "refreshable", False))

        if not requires_session and auth_mode is None and required_session_provider is None:
            return None

        return {
            "auth_mode": auth_mode,
            "requires_session": requires_session,
            "required_session_provider": required_session_provider,
            "refreshable": refreshable,
            "session_present": bool(self._normalize_optional_text(context.get("session_id"))),
        }

    def _affected_capabilities(
        self,
        *,
        capability_name: str,
        context: dict[str, Any],
    ) -> list[str]:
        """Return related capabilities that might be affected by this approval."""
        parts = capability_name.split(".")
        if len(parts) < 2:
            return []

        provider = parts[0]
        base = parts[1]
        related: list[str] = []

        related.append(f"{provider}.{base}.list")
        related.append(f"{provider}.{base}.get")

        rollback_suffixes = ("refund", "revert", "cancel", "undo")
        for suffix in rollback_suffixes:
            if base.endswith(suffix) or base == suffix:
                continue
            related.append(f"{provider}.{base}.{suffix}")

        return related[:5]

    def _data_classification(self, capability_name: str) -> str:
        """Determine data classification sensitivity from capability name."""
        lowered = capability_name.lower()

        sensitive_keywords = (
            "password", "secret", "credential", "token", "key", "auth",
            "ssn", "credit", "card", "bank", "pii", "personal",
        )
        if any(kw in lowered for kw in sensitive_keywords):
            return "sensitive"

        if "public" in lowered or "read" in lowered or "get" in lowered:
            return "public"

        return "internal"

    def _compliance_flags(self, capability_name: str) -> list[str]:
        """Return compliance-relevant flags based on capability name."""
        flags: list[str] = []
        lowered = capability_name.lower()

        if any(kw in lowered for kw in ("delete", "remove", "purge", "wipe")):
            flags.append("data_deletion")
        if any(kw in lowered for kw in ("export", "download", "backup")):
            flags.append("data_export")
        if any(kw in lowered for kw in ("admin", "root", "superuser", "owner")):
            flags.append("elevated_privilege")
        if any(kw in lowered for kw in ("payment", "billing", "invoice", "refund")):
            flags.append("financial_transaction")

        return flags

    def _time_sensitivity(self, capability_name: str) -> str:
        """Determine operational time sensitivity from capability name."""
        lowered = capability_name.lower()

        critical_suffixes = ("critical", "urgent", "emergency")
        for suffix in critical_suffixes:
            if suffix in lowered:
                return "critical"

        if "health" in lowered or "status" in lowered or "monitor" in lowered:
            return "real_time"

        if "batch" in lowered or "sync" in lowered or "import" in lowered:
            return "deferred"

        return "standard"

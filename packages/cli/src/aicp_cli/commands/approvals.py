"""Approval commands for the AICP CLI."""

from __future__ import annotations

import json
from typing import Any


def _normalize_record(record: Any) -> Any:
    """Normalize approval service return values for JSON output."""
    if record is None:
        return None

    if isinstance(record, (str, int, float, bool)):
        return record

    if isinstance(record, dict):
        return {k: _normalize_record(v) for k, v in record.items()}

    if isinstance(record, list):
        return [_normalize_record(item) for item in record]

    model_dump = getattr(record, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)

    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(record, "__dict__"):
        return {
            key: _normalize_record(value)
            for key, value in vars(record).items()
            if not key.startswith("_")
        }

    return str(record)


async def cmd_approvals_list(approval_service, args) -> int:
    """List approval requests."""
    del args

    try:
        approvals = await approval_service.list_approvals()
    except Exception as exc:
        print(json.dumps({"error": f"Failed to list approvals: {exc}"}))
        return 1

    print(json.dumps(_normalize_record(approvals), indent=2, default=str))
    return 0


async def cmd_approvals_decide(approval_service, args) -> int:
    """Apply an approval decision."""
    modified_arguments = None

    if getattr(args, "modified_arguments", None):
        try:
            modified_arguments = json.loads(args.modified_arguments)
        except json.JSONDecodeError as exc:
            print(
                json.dumps(
                    {
                        "error": "Invalid JSON in --modified-arguments",
                        "details": str(exc),
                    }
                )
            )
            return 1

    try:
        decision = await approval_service.decide(
            args.approval_id,
            decision=args.decision,
            approver=args.approver,
            reason=args.reason,
            modified_arguments=modified_arguments,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Failed to apply approval decision: {exc}",
                    "approval_id": args.approval_id,
                    "decision": args.decision,
                }
            )
        )
        return 1

    print(json.dumps(_normalize_record(decision), indent=2, default=str))
    return 0

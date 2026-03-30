"""Approval commands for the AICP CLI."""

import json


async def cmd_approvals_list(approval_service, args) -> int:
    """List approval requests."""
    del args
    approvals = await approval_service.list_approvals()
    print(json.dumps(approvals, indent=2))
    return 0


async def cmd_approvals_decide(approval_service, args) -> int:
    """Apply an approval decision."""
    modified_arguments = None
    if args.modified_arguments:
        try:
            modified_arguments = json.loads(args.modified_arguments)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in --modified-arguments")
            return 1

    decision = await approval_service.decide(
        args.approval_id,
        decision=args.decision,
        approver=args.approver,
        reason=args.reason,
        modified_arguments=modified_arguments,
    )
    print(json.dumps(decision, indent=2))
    return 0

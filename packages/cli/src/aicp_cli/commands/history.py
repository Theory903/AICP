"""History commands for the AICP CLI."""

import json


async def cmd_history_list(audit_service, args) -> int:
    """List audit history entries."""
    entries = await audit_service.list_entries(
        workflow_id=args.workflow_id,
        capability_name=args.capability_name,
        approval_request_id=args.approval_request_id,
    )
    print(json.dumps(entries, indent=2))
    return 0

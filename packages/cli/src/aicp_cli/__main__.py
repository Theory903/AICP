"""AICP CLI entry point.

Delegates to the click-based CLI in main.py.
Kept for backward compatibility with existing entry points.
"""

from __future__ import annotations

import argparse
import sys

from aicp_cli.main import cli


def create_parser() -> argparse.ArgumentParser:
    """Create the argparse-compatible CLI parser.

    Provides a minimal argparse parser that mirrors the AICP CLI command
    structure. Used by tests and tooling that require an argparse interface.
    """
    parser = argparse.ArgumentParser(prog="aicp", description="AICP CLI")
    subparsers = parser.add_subparsers(dest="command")

    # execute subcommand
    execute_parser = subparsers.add_parser("execute", help="Execute a capability")
    execute_parser.add_argument("capability", help="Capability name")
    execute_parser.add_argument("--args", default="{}", help="JSON arguments")
    execute_parser.add_argument("--context", default="{}", help="JSON context")

    # map subcommand with nested subcommands
    map_parser = subparsers.add_parser("map", help="Map external APIs to capabilities")
    map_subparsers = map_parser.add_subparsers(dest="map_command")
    map_openapi = map_subparsers.add_parser("openapi", help="Map OpenAPI spec")
    map_openapi.add_argument("spec", help="Path to OpenAPI spec")
    map_curl = map_subparsers.add_parser("curl", help="Map cURL command")
    map_curl.add_argument("command_text", nargs="?", help="cURL command")
    map_postman = map_subparsers.add_parser("postman", help="Map Postman collection")
    map_postman.add_argument("collection", nargs="?", help="Path to Postman collection")

    # approvals subcommand with nested subcommands
    approvals_parser = subparsers.add_parser("approvals", help="Manage approvals")
    approvals_subparsers = approvals_parser.add_subparsers(dest="approvals_command")
    approvals_list = approvals_subparsers.add_parser("list", help="List pending approvals")
    approvals_decide = approvals_subparsers.add_parser("decide", help="Decide on an approval")
    approvals_decide.add_argument("approval_id", help="Approval request ID")
    approvals_decide.add_argument("--decision", required=True, choices=["approved", "denied"])
    approvals_decide.add_argument("--approver", required=True, help="Approver identity")
    approvals_decide.add_argument("--reason", help="Decision reason")

    # history subcommand
    history_parser = subparsers.add_parser("history", help="View execution history")
    history_parser.add_argument("--workflow-id", dest="workflow_id", help="Filter by workflow ID")
    history_parser.add_argument("--capability-name", dest="capability_name", help="Filter by capability")

    return parser


def _system_exit_code(exc: SystemExit) -> int:
    """Normalize SystemExit.code into an integer exit status."""
    code = exc.code

    if code is None:
        return 0

    if isinstance(code, int):
        return code

    # Click and other CLI systems may exit with a message object/string.
    # In that case, stderr/stdout is already handled elsewhere, and the
    # process should still return a failure code.
    return 1


def main() -> int:
    """Run the AICP CLI and return a process exit code."""
    try:
        cli()
        return 0
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except SystemExit as exc:
        return _system_exit_code(exc)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

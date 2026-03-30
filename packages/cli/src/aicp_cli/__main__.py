"""AICP CLI - Command-line interface for AICP."""

import argparse
import asyncio
import sys

from aicp import AicpExecutor, AicpRegistry
from aicp.implementations import InMemoryCapabilityRepository
from aicp_runtime.persistence import FileRuntimeStore, InMemoryRuntimeStore
from aicp_runtime.services import ApprovalService, AuditService

from aicp_cli.commands.approvals import cmd_approvals_decide, cmd_approvals_list
from aicp_cli.commands.call import cmd_call
from aicp_cli.commands.discover import cmd_discover
from aicp_cli.commands.execute import cmd_execute
from aicp_cli.commands.history import cmd_history_list
from aicp_cli.commands.map_curl import cmd_map_curl
from aicp_cli.commands.map_har import cmd_map_har
from aicp_cli.commands.list import cmd_list
from aicp_cli.commands.map_openapi import cmd_map_openapi
from aicp_cli.commands.map_postman import cmd_map_postman
from aicp_cli.commands.register import cmd_register
from aicp_cli.commands.serve import cmd_serve


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aicp",
        description="AI Capability Protocol CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # register command
    register_parser = subparsers.add_parser("register", help="Register a capability")
    register_parser.add_argument("name", help="Capability name")
    register_parser.add_argument("description", help="Capability description")
    register_parser.add_argument(
        "kind", choices=["query", "action", "workflow"], help="Capability kind"
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List capabilities")

    # call command
    call_parser = subparsers.add_parser("call", help="Call a capability")
    call_parser.add_argument("name", help="Capability name")
    call_parser.add_argument("--args", default="{}", help="JSON arguments")

    # discover command
    discover_parser = subparsers.add_parser("discover", help="Discover capabilities")

    # execute command (P0)
    execute_parser = subparsers.add_parser("execute", help="Execute a capability")
    execute_parser.add_argument("capability", help="Capability name to execute")
    execute_parser.add_argument(
        "--args", default="{}", help="JSON arguments for the capability"
    )
    execute_parser.add_argument(
        "--context", default="{}", help="JSON context for execution"
    )

    # map subcommand (P0)
    map_parser = subparsers.add_parser("map", help="Map external specifications to capabilities")
    map_subparsers = map_parser.add_subparsers(dest="map_command", help="Map commands")

    # map openapi (P0)
    openapi_parser = map_subparsers.add_parser("openapi", help="Map OpenAPI specification to capabilities")
    openapi_parser.add_argument("file", help="Path to OpenAPI file (JSON or YAML)")
    openapi_parser.add_argument(
        "--name", help="Name for the capability source (defaults to file name)"
    )
    openapi_parser.add_argument(
        "--base-url", help="Base URL for the API (overrides OpenAPI servers)"
    )
    openapi_parser.add_argument(
        "--output", "-o", help="Output file for capabilities (default: stdout)"
    )

    postman_parser = map_subparsers.add_parser(
        "postman", help="Map Postman collection to capabilities"
    )
    postman_parser.add_argument("file", help="Path to Postman collection JSON")
    postman_parser.add_argument(
        "--name", help="Name for the capability source (defaults to file name)"
    )
    postman_parser.add_argument(
        "--output", "-o", help="Output file for capabilities (default: stdout)"
    )

    har_parser = map_subparsers.add_parser("har", help="Map HAR file to capabilities")
    har_parser.add_argument("file", help="Path to HAR file JSON")
    har_parser.add_argument(
        "--name", help="Name for the capability source (defaults to file name)"
    )
    har_parser.add_argument(
        "--output", "-o", help="Output file for capabilities (default: stdout)"
    )

    curl_parser = map_subparsers.add_parser("curl", help="Map cURL command to capabilities")
    curl_parser.add_argument("command_text", help="Full cURL command string")
    curl_parser.add_argument(
        "--name", help="Name for the capability source (defaults to curl-import)"
    )
    curl_parser.add_argument(
        "--output", "-o", help="Output file for capabilities (default: stdout)"
    )

    # serve command (P0)
    serve_parser = subparsers.add_parser("serve", help="Start AICP server")
    serve_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )
    serve_parser.add_argument(
        "--app", help="FastAPI app module path (e.g., myapp:app)"
    )
    serve_parser.add_argument(
        "--discovery-path", default="/aicp/discover", help="Discovery endpoint path"
    )
    serve_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload"
    )
    serve_parser.add_argument(
        "--store-path",
        help="Directory for durable runtime state; defaults to in-memory mode",
    )
    serve_parser.add_argument(
        "--store-backend",
        choices=["memory", "file", "sqlite"],
        default="memory",
        help="Persistence backend for runtime state",
    )

    approvals_parser = subparsers.add_parser("approvals", help="Approval queue operations")
    approvals_parser.add_argument(
        "--store-path",
        help="Directory for durable runtime state; defaults to in-memory mode",
    )
    approvals_parser.add_argument(
        "--store-backend",
        choices=["memory", "file", "sqlite"],
        default="memory",
        help="Persistence backend for governance state",
    )
    approvals_subparsers = approvals_parser.add_subparsers(
        dest="approvals_command", help="Approval commands"
    )
    approvals_subparsers.add_parser("list", help="List approval requests")
    decide_parser = approvals_subparsers.add_parser("decide", help="Apply approval decision")
    decide_parser.add_argument("approval_id", help="Approval request ID")
    decide_parser.add_argument("--decision", required=True, help="Decision value")
    decide_parser.add_argument("--approver", required=True, help="Approver identity")
    decide_parser.add_argument("--reason", help="Optional decision reason")
    decide_parser.add_argument(
        "--modified-arguments", help="Optional JSON payload with modified arguments"
    )

    history_parser = subparsers.add_parser("history", help="Audit history operations")
    history_parser.add_argument(
        "--store-path",
        help="Directory for durable runtime state; defaults to in-memory mode",
    )
    history_parser.add_argument(
        "--store-backend",
        choices=["memory", "file", "sqlite"],
        default="memory",
        help="Persistence backend for audit state",
    )
    history_parser.add_argument("--workflow-id", help="Filter by workflow ID")
    history_parser.add_argument("--capability-name", help="Filter by capability name")
    history_parser.add_argument("--approval-request-id", help="Filter by approval request ID")

    return parser


async def amain() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Handle map subcommand
    if args.command == "map":
        if not hasattr(args, "map_command") or not args.map_command:
            parser.print_help()
            return 1

        if args.map_command == "openapi":
            return await cmd_map_openapi(args)
        elif args.map_command == "postman":
            return await cmd_map_postman(args)
        elif args.map_command == "har":
            return await cmd_map_har(args)
        elif args.map_command == "curl":
            return await cmd_map_curl(args)
        else:
            print(f"Unknown map command: {args.map_command}")
            return 1

    # Handle serve command separately (blocking)
    if args.command == "serve":
        return await cmd_serve(args)

    if args.command in {"approvals", "history"}:
        if args.store_backend == "sqlite":
            from aicp_runtime.persistence import SqliteRuntimeStore

            runtime_store = SqliteRuntimeStore(args.store_path or ".aicp-runtime.db")
        elif args.store_path:
            runtime_store = FileRuntimeStore(args.store_path)
        else:
            runtime_store = InMemoryRuntimeStore()
        approval_service = ApprovalService(runtime_store)
        audit_service = AuditService(runtime_store)

        if args.command == "approvals":
            if not getattr(args, "approvals_command", None):
                parser.print_help()
                return 1
            if args.approvals_command == "list":
                return await cmd_approvals_list(approval_service, args)
            if args.approvals_command == "decide":
                return await cmd_approvals_decide(approval_service, args)
        if args.command == "history":
            return await cmd_history_list(audit_service, args)

    # Create registry and executor for other commands
    repo = InMemoryCapabilityRepository()
    registry = AicpRegistry()
    executor = AicpExecutor(repo)

    if args.command == "register":
        return await cmd_register(registry, args)
    elif args.command == "list":
        return await cmd_list(registry, args)
    elif args.command == "call":
        return await cmd_call(registry, executor, args)
    elif args.command == "discover":
        return await cmd_discover(registry, args)
    elif args.command == "execute":
        return await cmd_execute(registry, executor, args)
    else:
        parser.print_help()
        return 1


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())

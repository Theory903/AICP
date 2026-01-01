"""AICP CLI - Command-line interface for AICP."""

import argparse
import asyncio
import json
import sys

from aicp import AicpRegistry, AicpExecutor, Capability, CapabilityKind
from aicp.implementations import InMemoryCapabilityRepository


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aicp",
        description="AI Capability Protocol CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    register_parser = subparsers.add_parser("register", help="Register a capability")
    register_parser.add_argument("name", help="Capability name")
    register_parser.add_argument("description", help="Capability description")
    register_parser.add_argument(
        "kind", choices=["query", "action", "workflow"], help="Capability kind"
    )

    list_parser = subparsers.add_parser("list", help="List capabilities")

    call_parser = subparsers.add_parser("call", help="Call a capability")
    call_parser.add_argument("name", help="Capability name")
    call_parser.add_argument("--args", default="{}", help="JSON arguments")

    discover_parser = subparsers.add_parser("discover", help="Discover capabilities")

    return parser


async def cmd_register(registry: AicpRegistry, args: argparse.Namespace) -> int:
    cap = Capability(
        name=args.name,
        description=args.description,
        kind=CapabilityKind(args.kind),
    )
    registry.register_capability(cap)
    print(f"Registered: {args.name}")
    return 0


async def cmd_list(registry: AicpRegistry, args: argparse.Namespace) -> int:
    caps = registry.list_capabilities()
    if not caps:
        print("No capabilities registered")
        return 0
    for cap in caps:
        print(f"  {cap.name} ({cap.kind}) - {cap.description}")
    return 0


async def cmd_call(
    registry: AicpRegistry, executor: AicpExecutor, args: argparse.Namespace
) -> int:
    try:
        import json

        call_args = json.loads(args.args)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in --args")
        return 1

    result = await executor.execute(args.name, call_args)
    print(json.dumps(result.model_dump(), indent=2))
    return 0 if result.status == "success" else 1


async def cmd_discover(registry: AicpRegistry, args: argparse.Namespace) -> int:
    discovery = registry.discovery_response()
    print(json.dumps(discovery, indent=2))
    return 0


async def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

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
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

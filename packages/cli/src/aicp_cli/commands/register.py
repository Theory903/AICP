"""Register command for the AICP CLI."""

from aicp import Capability, CapabilityKind


async def cmd_register(registry, args) -> int:
    """Register a capability in the local registry."""
    cap = Capability(
        name=args.name,
        description=args.description,
        kind=CapabilityKind(args.kind),
    )
    registry.register_capability(cap)
    print(f"Registered: {args.name}")
    return 0

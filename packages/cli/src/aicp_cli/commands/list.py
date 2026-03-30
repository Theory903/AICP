"""List command for the AICP CLI."""


async def cmd_list(registry, args) -> int:
    """List capabilities in the local registry."""
    del args
    caps = registry.list_capabilities()
    if not caps:
        print("No capabilities registered")
        return 0
    for cap in caps:
        print(f"  {cap.name} ({cap.kind}) - {cap.description}")
    return 0

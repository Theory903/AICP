import asyncio

from aicp.plugins import HookContext, HookRegistry, HookType


def test_hook_registry_runs_handlers_in_priority_order() -> None:
    registry = HookRegistry()
    calls: list[str] = []

    async def slow_first(context: HookContext) -> str:
        calls.append(f"async:{context.plugin_id}")
        return context.plugin_id

    def sync_second(context: HookContext) -> str:
        calls.append(f"sync:{context.plugin_id}")
        return context.plugin_id

    registry.register(HookType.PRE_CAPABILITY, "second", sync_second, priority=50)
    registry.register(HookType.PRE_CAPABILITY, "first", slow_first, priority=10)

    results = asyncio.run(
        registry.emit(HookType.PRE_CAPABILITY, payload={"capability": "demo.echo"}, execution_id="exec-1")
    )

    assert calls == ["async:first", "sync:second"]
    assert [result.plugin_id for result in results] == ["first", "second"]


def test_hook_registry_unregisters_plugin_handlers() -> None:
    registry = HookRegistry()

    def handler(context: HookContext) -> None:
        return None

    registry.register(HookType.ON_STARTUP, "demo.echo", handler)
    registry.unregister_plugin("demo.echo")

    results = asyncio.run(registry.emit(HookType.ON_STARTUP, payload={}))

    assert results == []

from __future__ import annotations

import pytest

from aicp.channels import ChannelManifest, ChannelNotFound, ChannelRegistry, ChannelRouter, ChannelType, ConsoleChannel


@pytest.mark.asyncio
async def test_route_to_message_channel() -> None:
    registry = ChannelRegistry()
    channel = ConsoleChannel("console")
    await channel.connect()
    registry.register(
        ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE),
        channel,
    )
    router = ChannelRouter(registry)

    assert router.route("console") == "console"


def test_fallback_when_channel_unavailable() -> None:
    registry = ChannelRegistry()
    registry.register(
        ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE, priority=50),
        ConsoleChannel("console"),
    )
    router = ChannelRouter(registry)
    router.set_fallback("fallback")

    assert router.route("console") == "fallback"


def test_fallback_when_no_enabled_channels() -> None:
    registry = ChannelRegistry()
    registry.register(
        ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE, enabled=False),
        ConsoleChannel("console"),
    )
    router = ChannelRouter(registry)
    router.set_fallback("fallback")

    assert router.route() == "fallback"


def test_route_raises_when_no_enabled_or_fallback() -> None:
    registry = ChannelRegistry()
    router = ChannelRouter(registry)

    with pytest.raises(ChannelNotFound):
        router.route()

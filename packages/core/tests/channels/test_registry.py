from __future__ import annotations

import pytest

from aicp.channels import ChannelManifest, ChannelNotFound, ChannelRegistry, ChannelType, ConsoleChannel


def test_register_and_get() -> None:
    registry = ChannelRegistry()
    manifest = ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE)
    channel = ConsoleChannel("console")

    registry.register(manifest, channel)

    assert registry.get("console") is channel


def test_list_by_type() -> None:
    registry = ChannelRegistry()
    registry.register(
        ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE),
        ConsoleChannel("console"),
    )
    registry.register(
        ChannelManifest(id="api", name="Api", channel_type=ChannelType.API),
        ConsoleChannel("api"),
    )

    assert registry.list_by_type(ChannelType.CONSOLE) == ["console"]
    assert registry.list_by_type(ChannelType.API) == ["api"]


def test_list_enabled() -> None:
    registry = ChannelRegistry()
    registry.register(
        ChannelManifest(id="console", name="Console", channel_type=ChannelType.CONSOLE, enabled=True),
        ConsoleChannel("console"),
    )
    registry.register(
        ChannelManifest(id="api", name="Api", channel_type=ChannelType.API, enabled=False),
        ConsoleChannel("api"),
    )

    assert registry.list_enabled() == ["console"]


def test_channel_not_found() -> None:
    registry = ChannelRegistry()

    with pytest.raises(ChannelNotFound):
        registry.get("missing")

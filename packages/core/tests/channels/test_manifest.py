from __future__ import annotations

import pytest
from pydantic import ValidationError

from aicp.channels import ChannelManifest, ChannelType


def test_valid_manifest() -> None:
    manifest = ChannelManifest(
        id="console",
        name="Console",
        channel_type=ChannelType.CONSOLE,
        priority=10,
    )

    assert manifest.id == "console"
    assert manifest.name == "Console"
    assert manifest.channel_type is ChannelType.CONSOLE
    assert manifest.enabled is True
    assert manifest.priority == 10


def test_empty_id_rejected() -> None:
    with pytest.raises(ValidationError):
        ChannelManifest(id="   ", name="Console", channel_type=ChannelType.CONSOLE)

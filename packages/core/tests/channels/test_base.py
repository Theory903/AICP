from __future__ import annotations

from aicp.channels import ChannelError, ChannelUnavailable


def test_channel_error() -> None:
    error = ChannelError("boom")

    assert str(error) == "boom"


def test_channel_unavailable() -> None:
    error = ChannelUnavailable("console")

    assert error.channel_id == "console"
    assert str(error) == "Channel unavailable: console"

from __future__ import annotations

from aicp.channels import ChannelMessage, ChannelResponse


def test_channel_message_creation_with_defaults() -> None:
    message = ChannelMessage(channel_id="console", sender_id="user-1", content="hello")

    assert message.id
    assert message.channel_id == "console"
    assert message.sender_id == "user-1"
    assert message.content == "hello"
    assert message.timestamp
    assert message.metadata == {}
    assert message.attachments == []


def test_channel_response_creation() -> None:
    response = ChannelResponse(channel_id="api", content="ok")

    assert response.id
    assert response.channel_id == "api"
    assert response.content == "ok"
    assert response.format_hint == "text"
    assert response.metadata == {}

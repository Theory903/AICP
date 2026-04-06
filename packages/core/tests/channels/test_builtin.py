from __future__ import annotations

from io import StringIO

import pytest

from aicp.channels import ApiChannel, ChannelMessage, ChannelResponse, ConsoleChannel, WebhookChannel


@pytest.mark.asyncio
async def test_console_channel_connect_and_send(capsys: pytest.CaptureFixture[str]) -> None:
    channel = ConsoleChannel("console")

    await channel.connect()
    await channel.send(ChannelResponse(channel_id="console", content="hello"))

    captured = capsys.readouterr()
    assert channel.connected is True
    assert "hello" in captured.out


@pytest.mark.asyncio
async def test_webhook_channel_connect_send_receive() -> None:
    channel = WebhookChannel("webhook", webhook_url="https://example.com/webhook")
    message = ChannelMessage(channel_id="webhook", sender_id="user-1", content="payload")
    response = ChannelResponse(channel_id="webhook", content="ok")

    await channel.connect()
    channel.accept(message)
    await channel.send(response)

    assert await channel.health_check() is True
    assert await channel.receive() == message
    assert channel.last_response == response


@pytest.mark.asyncio
async def test_api_channel_connect_send_receive() -> None:
    channel = ApiChannel("api")
    message = ChannelMessage(channel_id="api", sender_id="user-1", content="request")
    response = ChannelResponse(channel_id="api", content="ok")

    await channel.connect()
    channel.push_message(message)
    await channel.send(response)

    assert await channel.health_check() is True
    assert await channel.receive() == message
    assert channel.last_response == response

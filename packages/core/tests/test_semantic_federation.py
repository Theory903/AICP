import sys
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

from aicp.discovery.semantic import OpenAIEmbeddingProvider
from aicp.federation.federation import CapabilityShare, RegistrySyncStrategy
from aicp.federation.http_provider import HttpFederationProvider


def _capability_share() -> CapabilityShare:
    return CapabilityShare(
        capability_name="notes.create",
        version="1.0.0",
        shared_by="node-a",
        shared_at="2026-04-05T10:00:00Z",
    )


def test_openai_embedding_provider_raises_helpful_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key")
    original_import = __import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
        if name == "openai":
            raise ImportError("missing openai")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(ImportError, match="openai package required: pip install openai"):
        provider.embed(["hello"])


def test_openai_embedding_provider_calls_openai_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            calls["api_key"] = api_key
            self.embeddings = SimpleNamespace(create=self._create)

        def _create(self, *, model: str, input: list[str], encoding_format: str) -> SimpleNamespace:
            calls["model"] = model
            calls["input"] = input
            calls["encoding_format"] = encoding_format
            return SimpleNamespace(
                data=[
                    SimpleNamespace(embedding=[0.1, 0.2]),
                    SimpleNamespace(embedding=[0.3, 0.4]),
                ]
            )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    provider = OpenAIEmbeddingProvider(api_key="secret", model="text-embedding-3-small")

    assert provider.embed(["alpha", "beta"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert calls == {
        "api_key": "secret",
        "model": "text-embedding-3-small",
        "input": ["alpha", "beta"],
        "encoding_format": "float",
    }


@pytest.mark.asyncio
async def test_register_capability_posts_to_remote_endpoint() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["json"] = request.content.decode()
        return httpx.Response(200, json={"status": "ok", "registered": True})

    provider = HttpFederationProvider(node_endpoint="https://mesh.example")
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=provider.timeout)

    result = await provider.register_capability(_capability_share())

    assert result == {"status": "ok", "registered": True}
    assert seen["method"] == "POST"
    assert seen["url"] == "https://mesh.example/v1/federation/register"
    assert '"capability_name":"notes.create"' in str(seen["json"])

    await provider.close()


@pytest.mark.asyncio
async def test_register_capability_without_endpoint_returns_error_dict() -> None:
    provider = HttpFederationProvider()

    result = await provider.register_capability(_capability_share())

    assert result["status"] == "error"
    assert "node endpoint" in result["reason"].lower()

    await provider.close()


@pytest.mark.asyncio
async def test_sync_registry_fetches_remote_registry() -> None:
    payload = {
        "id": "reg_123",
        "name": "mesh",
        "node_id": "remote-node",
        "entries": {"notes.create": {"version": 1}},
        "vector_clock": {"remote-node": 3},
        "last_updated": "2026-04-05T10:00:00",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://mesh.example/v1/federation/registry"
        return httpx.Response(200, json=payload)

    provider = HttpFederationProvider(node_endpoint="https://mesh.example")
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=provider.timeout)

    registry = await provider.sync_registry(RegistrySyncStrategy("crdt"))

    assert getattr(registry, "id") == "reg_123"
    assert getattr(registry, "name") == "mesh"
    assert getattr(registry, "node_id") == "remote-node"
    assert getattr(registry, "get")("notes.create") == {"version": 1}
    assert getattr(registry, "vector_clock") == {"remote-node": 3}
    assert getattr(registry, "last_updated") == "2026-04-05T10:00:00"

    await provider.close()


@pytest.mark.asyncio
async def test_sync_registry_without_endpoint_returns_empty_registry() -> None:
    provider = HttpFederationProvider()

    registry = await provider.sync_registry(RegistrySyncStrategy("crdt"))

    assert getattr(registry, "name") == "default"
    assert getattr(registry, "node_id") == "local"
    assert getattr(registry, "entries") == {}
    assert getattr(registry, "vector_clock") == {}
    datetime.fromisoformat(getattr(registry, "last_updated"))

    await provider.close()

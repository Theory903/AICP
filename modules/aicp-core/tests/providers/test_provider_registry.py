from __future__ import annotations

import pytest

from aicp.providers.manifest import ProviderManifest, ProviderType
from aicp.providers.registry import ProviderNotFoundError, ProviderRegistry


def make_manifest(
    provider_id: str,
    provider_type: ProviderType,
    capabilities: list[str],
) -> ProviderManifest:
    return ProviderManifest(
        id=provider_id,
        name=provider_id.title(),
        provider_type=provider_type,
        base_url=f"https://{provider_id}.example.com",
        api_key_env=f"{provider_id.upper()}_API_KEY",
        models=[f"{provider_id}-model"],
        capabilities=capabilities,
    )


class TestProviderRegistry:
    def test_register_and_get(self) -> None:
        registry = ProviderRegistry()
        manifest = make_manifest("openai-primary", ProviderType.OPENAI, ["chat"])

        registry.register(manifest)

        assert registry.get("openai-primary") == manifest
        assert registry.list_all() == [manifest]

    def test_list_by_type(self) -> None:
        registry = ProviderRegistry()
        openai = make_manifest("openai-primary", ProviderType.OPENAI, ["chat"])
        anthropic = make_manifest("anthropic-backup", ProviderType.ANTHROPIC, ["chat"])
        registry.register(openai)
        registry.register(anthropic)

        assert registry.list_by_type(ProviderType.OPENAI) == [openai]
        assert registry.list_by_type(ProviderType.GOOGLE) == []

    def test_list_by_capability(self) -> None:
        registry = ProviderRegistry()
        chat_only = make_manifest("chat-only", ProviderType.OPENAI, ["chat"])
        embeddings = make_manifest("embedder", ProviderType.GOOGLE, ["embedding", "chat"])
        registry.register(chat_only)
        registry.register(embeddings)

        assert registry.list_by_capability("embedding") == [embeddings]
        assert registry.list_by_capability("chat") == [chat_only, embeddings]

    def test_provider_not_found_on_missing(self) -> None:
        registry = ProviderRegistry()

        with pytest.raises(ProviderNotFoundError):
            registry.health_check("missing")

from __future__ import annotations

import pytest

from aicp.providers.manifest import ProviderManifest, ProviderType
from aicp.providers.registry import ProviderRegistry
from aicp.providers.router import FallbackChain, ProviderRouter


def make_manifest(provider_id: str) -> ProviderManifest:
    return ProviderManifest(
        id=provider_id,
        name=provider_id,
        provider_type=ProviderType.OPENAI,
        base_url=f"https://{provider_id}.example.com",
        api_key_env=f"{provider_id.upper()}_API_KEY",
        models=["gpt-4o"],
        capabilities=["chat"],
    )


class TestFallbackChain:
    def test_fallback_chain_creation(self) -> None:
        chain = FallbackChain(
            primary_id="primary",
            fallback_ids=["secondary", "tertiary"],
            max_retries=2,
        )

        assert chain.primary_id == "primary"
        assert chain.fallback_ids == ["secondary", "tertiary"]
        assert chain.current_index == 0


class TestProviderRouter:
    def test_auto_failover_on_failure(self) -> None:
        registry = ProviderRegistry()
        for provider_id in ["primary", "secondary", "tertiary"]:
            registry.register(make_manifest(provider_id))
        router = ProviderRouter(registry)
        router.add_chain(
            "default",
            FallbackChain(
                primary_id="primary",
                fallback_ids=["secondary", "tertiary"],
                max_retries=2,
            ),
        )

        assert router.route("default") == "primary"

        router.record_failure("default")
        assert router.route("default") == "secondary"

        router.record_failure("default")
        assert router.route("default") == "tertiary"

    def test_reset_to_primary_on_success(self) -> None:
        registry = ProviderRegistry()
        for provider_id in ["primary", "secondary"]:
            registry.register(make_manifest(provider_id))
        router = ProviderRouter(registry)
        router.add_chain(
            "default",
            FallbackChain(primary_id="primary", fallback_ids=["secondary"], max_retries=1),
        )

        router.record_failure("default")
        assert router.route("default") == "secondary"

        router.record_success("default")
        assert router.route("default") == "primary"

    def test_exhaustion_all_fallbacks_failed(self) -> None:
        registry = ProviderRegistry()
        for provider_id in ["primary", "secondary"]:
            registry.register(make_manifest(provider_id))
        router = ProviderRouter(registry)
        router.add_chain(
            "default",
            FallbackChain(primary_id="primary", fallback_ids=["secondary"], max_retries=1),
        )

        router.record_failure("default")
        router.record_failure("default")

        with pytest.raises(RuntimeError, match="No providers available"):
            router.route("default")

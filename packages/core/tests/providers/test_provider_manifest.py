from __future__ import annotations

import pytest
from pydantic import ValidationError

from aicp.providers.manifest import ProviderManifest, ProviderType


class TestProviderManifest:
    def test_valid_manifest_creation(self) -> None:
        manifest = ProviderManifest(
            id="openai-primary",
            name="OpenAI Primary",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            models=["gpt-4.1", "gpt-4o"],
            capabilities=["chat", "streaming", "vision"],
            max_tokens=128000,
            rate_limit_rpm=5000,
            timeout_seconds=45,
        )

        assert manifest.id == "openai-primary"
        assert manifest.provider_type == ProviderType.OPENAI
        assert manifest.capabilities == ["chat", "streaming", "vision"]

    def test_invalid_manifest_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProviderManifest(
                id="",
                name="Bad",
                provider_type="invalid",  # type: ignore[arg-type]
                base_url="https://example.com",
                api_key_env="API_KEY",
                models=["model"],
                capabilities=["chat"],
            )

    def test_capabilities_deduplication(self) -> None:
        manifest = ProviderManifest(
            id="dedupe",
            name="Dedupe",
            provider_type=ProviderType.ANTHROPIC,
            base_url="https://api.anthropic.com",
            api_key_env="ANTHROPIC_API_KEY",
            models=["claude-3-7-sonnet"],
            capabilities=["chat", "streaming", "chat", "vision", "streaming"],
        )

        assert manifest.capabilities == ["chat", "streaming", "vision"]

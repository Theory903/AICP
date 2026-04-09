from __future__ import annotations

from aicp.providers.models import ModelAlias, ModelRegistry


class TestModelRegistry:
    def test_alias_resolution(self) -> None:
        registry = ModelRegistry()
        registry.register(
            ModelAlias(
                alias="gpt-4",
                actual_model_id="gpt-4-0613",
                provider_id="openai-primary",
                pinned=True,
            )
        )

        assert registry.resolve("gpt-4", "openai-primary") == "gpt-4-0613"

    def test_fallback_to_alias_if_no_provider_match(self) -> None:
        registry = ModelRegistry()
        registry.register(
            ModelAlias(
                alias="smart-latest",
                actual_model_id="claude-3-7-sonnet-latest",
                provider_id="anthropic-primary",
                pinned=False,
            )
        )

        assert registry.resolve("smart-latest", "missing-provider") == "claude-3-7-sonnet-latest"
        assert registry.list_aliases("anthropic-primary") == ["smart-latest"]

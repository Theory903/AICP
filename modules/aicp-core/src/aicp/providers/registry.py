from __future__ import annotations

from .manifest import ProviderManifest, ProviderType


class ProviderError(Exception):
    pass


class ProviderNotFoundError(ProviderError):
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"Provider not found: {provider_id}")


class ProviderUnavailableError(ProviderError, RuntimeError):
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"Provider unavailable: {provider_id}")


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderManifest] = {}

    def register(self, manifest: ProviderManifest) -> ProviderManifest:
        self._providers[manifest.id] = manifest
        return manifest

    def get(self, provider_id: str) -> ProviderManifest | None:
        return self._providers.get(provider_id)

    def require(self, provider_id: str) -> ProviderManifest:
        provider = self.get(provider_id)
        if provider is None:
            raise ProviderNotFoundError(provider_id)
        return provider

    def list_all(self) -> list[ProviderManifest]:
        return [self._providers[key] for key in sorted(self._providers)]

    def list_by_type(self, provider_type: ProviderType) -> list[ProviderManifest]:
        return [provider for provider in self.list_all() if provider.provider_type == provider_type]

    def list_by_capability(self, capability: str) -> list[ProviderManifest]:
        return [provider for provider in self.list_all() if capability in provider.capabilities]

    def health_check(self, provider_id: str) -> bool:
        provider = self.require(provider_id)
        return bool(provider.base_url and provider.models)

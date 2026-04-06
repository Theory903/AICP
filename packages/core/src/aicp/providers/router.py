from __future__ import annotations

from dataclasses import dataclass, field

from .registry import ProviderRegistry, ProviderUnavailable


@dataclass(slots=True)
class FallbackChain:
    primary_id: str
    fallback_ids: list[str] = field(default_factory=list)
    max_retries: int = 3
    current_index: int = 0

    def provider_ids(self) -> list[str]:
        return [self.primary_id, *self.fallback_ids]

    def reset(self) -> None:
        self.current_index = 0


class ProviderRouter:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry
        self._chains: dict[str, FallbackChain] = {}

    def add_chain(self, name: str, chain: FallbackChain) -> None:
        for provider_id in chain.provider_ids():
            self._registry.require(provider_id)
        self._chains[name] = chain

    def route(self, chain_name: str) -> str:
        chain = self._require_chain(chain_name)
        provider_ids = chain.provider_ids()
        for index in range(chain.current_index, len(provider_ids)):
            provider_id = provider_ids[index]
            if self._registry.health_check(provider_id):
                chain.current_index = index
                return provider_id
        chain.current_index = len(provider_ids)
        raise ProviderUnavailable("No providers available")

    def record_failure(self, chain_name: str) -> None:
        chain = self._require_chain(chain_name)
        next_index = chain.current_index + 1
        chain.current_index = min(next_index, len(chain.provider_ids()))

    def record_success(self, chain_name: str) -> None:
        self._require_chain(chain_name).reset()

    def _require_chain(self, chain_name: str) -> FallbackChain:
        chain = self._chains.get(chain_name)
        if chain is None:
            raise KeyError(f"Unknown provider chain: {chain_name}")
        return chain

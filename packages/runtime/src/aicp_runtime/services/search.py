from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class SearchProvider(str, Enum):
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    EXA = "exa"
    TAVILY = "tavily"
    SEARXNG = "searxng"


class SearchError(AicpError):
    pass


class SearchProviderError(SearchError):
    pass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    score: float
    published_date: Optional[str] = None


class SearchConfig(BaseModel):
    query: str = Field(..., min_length=1)
    provider: SearchProvider = SearchProvider.BRAVE
    num_results: int = Field(default=10, ge=1, le=50)
    safe_search: bool = True


class CacheEntry:
    def __init__(self, results: list[SearchResult], ttl_seconds: int = 300):
        import time

        self.results = results
        self.expires_at = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        import time

        return time.time() > self.expires_at


class SearchService:
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._provider_health: dict[str, bool] = {p.value: True for p in SearchProvider}

    def _normalize_query(self, query: str) -> str:
        return query.lower().strip()

    def _get_cache_key(self, query: str, provider: str) -> str:
        return f"{provider}:{self._normalize_query(query)}"

    def _mock_search(self, query: str, provider: SearchProvider, num_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Result {i+1} for '{query}'",
                url=f"https://example.com/result{i+1}",
                snippet=f"This is a mock search result {i+1} for the query '{query}' from {provider.value}",
                provider=provider.value,
                score=1.0 - (i * 0.1),
            )
            for i in range(min(num_results, 5))
        ]

    def search(self, query: str, provider: Optional[SearchProvider] = None, num_results: Optional[int] = None) -> list[SearchResult]:
        provider = provider or SearchProvider.BRAVE
        num = num_results or 10

        cache_key = self._get_cache_key(query, provider.value)
        if cache_key in self._cache and not self._cache[cache_key].is_expired():
            return self._cache[cache_key].results[:num]

        if not self._provider_health.get(provider.value, False):
            return self.search_with_fallback(query, num_results=num)

        results = self._mock_search(query, provider, num)
        self._cache[cache_key] = CacheEntry(results)
        return results

    def search_with_fallback(self, query: str, providers: Optional[list[SearchProvider]] = None, num_results: Optional[int] = None) -> list[SearchResult]:
        providers = providers or [SearchProvider.BRAVE, SearchProvider.DUCKDUCKGO, SearchProvider.EXA]
        num = num_results or 10

        for provider in providers:
            if self._provider_health.get(provider.value, True):
                try:
                    results = self._mock_search(query, provider, num)
                    cache_key = self._get_cache_key(query, provider.value)
                    self._cache[cache_key] = CacheEntry(results)
                    return results
                except Exception:
                    self._provider_health[provider.value] = False
        raise SearchProviderError("All search providers failed")

    def get_provider_health(self, provider: SearchProvider) -> bool:
        return self._provider_health.get(provider.value, True)

    def clear_cache(self) -> None:
        self._cache.clear()

    def clear_cache_for_query(self, query: str) -> None:
        normalized = self._normalize_query(query)
        keys_to_remove = [k for k in self._cache.keys() if k.endswith(normalized)]
        for key in keys_to_remove:
            del self._cache[key]

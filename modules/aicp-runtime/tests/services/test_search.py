
from aicp_runtime.services.search import (
    SearchProvider,
    SearchResult,
    SearchService,
)


class TestSearchService:
    def test_search_brave(self):
        svc = SearchService()
        results = svc.search("test query", provider=SearchProvider.BRAVE, num_results=5)
        assert len(results) <= 5
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_duckduckgo(self):
        svc = SearchService()
        results = svc.search("test", provider=SearchProvider.DUCKDUCKGO)
        assert len(results) > 0

    def test_search_exa(self):
        svc = SearchService()
        results = svc.search("test", provider=SearchProvider.EXA)
        assert len(results) > 0

    def test_caching(self):
        svc = SearchService()
        results1 = svc.search("cached query")
        results2 = svc.search("cached query")
        assert len(results1) == len(results2)

    def test_cache_cleared(self):
        svc = SearchService()
        svc.search("clear me")
        svc.clear_cache_for_query("clear me")
        assert True

    def test_provider_health(self):
        svc = SearchService()
        assert svc.get_provider_health(SearchProvider.BRAVE) is True

    def test_fallback(self):
        svc = SearchService()
        results = svc.search_with_fallback("test", providers=[SearchProvider.BRAVE, SearchProvider.DUCKDUCKGO])
        assert len(results) > 0


class TestSearchResult:
    def test_result_creation(self):
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Test snippet",
            provider="brave",
            score=0.9,
        )
        assert result.title == "Test"
        assert result.score == 0.9
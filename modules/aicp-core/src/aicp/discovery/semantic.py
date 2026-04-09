"""
Semantic Discovery Engine Module
Module 11 - Semantic retrieval with embeddings
"""

from abc import ABC, abstractmethod
from collections import defaultdict

import numpy as np
from pydantic import BaseModel, Field


class EmbeddingResult(BaseModel):
    """Result from embedding generation"""
    text: str
    embedding: list[float]
    model: str


class SemanticSearchResult(BaseModel):
    """Semantic search result with score"""
    capability_name: str
    score: float
    description: str
    tags: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)


class SemanticDiscovery:
    """
    Semantic capability discovery using embeddings
    Supports keyword + semantic hybrid search
    """

    def __init__(self, embedding_dim: int = 384):
        self._embedding_dim = embedding_dim
        self._capability_embeddings: dict[str, list[float]] = {}
        self._capability_texts: dict[str, str] = {}
        self._keyword_index: dict[str, set[str]] = defaultdict(set)
        self._embeddings_available = False

        # Fallback keyword weights
        self._keyword_weight = 0.4
        self._semantic_weight = 0.6

    def index_capability(self, name: str, description: str, tags: list[str] | None = None):
        """Index a capability for semantic search"""
        self._capability_texts[name] = f"{name} {description} {' '.join(tags or [])}"

        # Build keyword index
        terms = name.lower().split('.')
        terms += description.lower().split()
        if tags:
            terms += [tag.lower() for tag in tags]

        for term in terms:
            if len(term) > 2:
                self._keyword_index[term].add(name)

    def set_embeddings(self, capability_embeddings: dict[str, list[float]]):
        """Set pre-computed embeddings for capabilities"""
        self._capability_embeddings = capability_embeddings
        self._embeddings_available = True

    def compute_embedding(self, text: str) -> list[float]:
        """Compute embedding for text using simple hash-based approach"""
        # Simple hash-based embedding for demo (replace with actual embedding model)
        np.random.seed(hash(text) % (2**32))
        return list(np.random.randn(self._embedding_dim).astype(float))

    def compute_capability_embedding(self, name: str) -> list[float]:
        """Compute or retrieve embedding for a capability"""
        if name in self._capability_embeddings:
            return self._capability_embeddings[name]

        text = self._capability_texts.get(name, name)
        embedding = self.compute_embedding(text)
        self._capability_embeddings[name] = embedding
        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors"""
        a_np = np.array(a)
        b_np = np.array(b)

        dot = np.dot(a_np, b_np)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    def _keyword_score(self, query: str, capability_name: str) -> float:
        """Compute keyword match score"""
        query_terms = set(query.lower().split())

        # Direct name match
        if query.lower() in capability_name.lower():
            return 1.0

        # Partial match
        name_parts = set(capability_name.lower().split('.'))
        overlap = query_terms & name_parts
        if overlap:
            return len(overlap) / max(len(query_terms), 1)

        # Keyword index match
        capability_keywords = set()
        for term in self._keyword_index:
            if capability_name in self._keyword_index[term]:
                capability_keywords.add(term)

        if capability_keywords:
            return len(query_terms & capability_keywords) / len(query_terms)

        return 0.0

    def search(
        self,
        query: str,
        capability_names: list[str],
        limit: int = 10,
        hybrid: bool = True
    ) -> list[SemanticSearchResult]:
        """
        Search capabilities semantically

        Args:
            query: Search query
            capability_names: List of capability names to search
            limit: Maximum results
            hybrid: Use hybrid keyword + semantic search

        Returns:
            Ranked list of matching capabilities
        """
        results = []

        for name in capability_names:
            score = 0.0
            matched_terms = []

            if hybrid and self._embeddings_available:
                # Semantic similarity
                query_embedding = self.compute_embedding(query)
                cap_embedding = self.compute_capability_embedding(name)
                semantic_score = self._cosine_similarity(query_embedding, cap_embedding)
                score = semantic_score * self._semantic_weight

                # Keyword boost
                keyword_score = self._keyword_score(query, name)
                score += keyword_score * self._keyword_weight

                if keyword_score > 0:
                    matched_terms.append("keyword")
                if semantic_score > 0.5:
                    matched_terms.append("semantic")
            else:
                # Keyword-only search
                score = self._keyword_score(query, name)
                if score > 0:
                    matched_terms.append("keyword")

            if score > 0:
                description = self._capability_texts.get(name, "")
                tags = []  # Would get from capability metadata

                results.append(SemanticSearchResult(
                    capability_name=name,
                    score=score,
                    description=description,
                    tags=tags,
                    matched_terms=matched_terms
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def find_related(self, capability_name: str, limit: int = 5) -> list[SemanticSearchResult]:
        """Find related capabilities using semantic similarity"""
        if not self._embeddings_available:
            # Fallback to keyword-based related
            related = []
            cap_parts = capability_name.split('.')
            for name in self._capability_texts:
                if name != capability_name and any(p in name for p in cap_parts):
                    related.append(SemanticSearchResult(
                        capability_name=name,
                        score=0.5,
                        description=self._capability_texts.get(name, ""),
                        matched_terms=["namespace"]
                    ))
            return related[:limit]

        # Semantic similarity
        cap_embedding = self.compute_capability_embedding(capability_name)

        results = []
        for name in self._capability_texts:
            if name != capability_name:
                other_embedding = self.compute_capability_embedding(name)
                score = self._cosine_similarity(cap_embedding, other_embedding)

                results.append(SemanticSearchResult(
                    capability_name=name,
                    score=score,
                    description=self._capability_texts.get(name, ""),
                    matched_terms=["semantic"]
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]


class EmbeddingProvider(ABC):
    """Abstract embedding provider"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts"""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-small provider"""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            import openai
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e

        client = openai.OpenAI(api_key=self._api_key)
        response = client.embeddings.create(
            model=self._model,
            input=texts,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embedding provider"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self._base_url = base_url
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama"""
        import requests

        embeddings = []
        for text in texts:
            response = requests.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text}
            )
            if response.ok:
                embeddings.append(response.json()["embedding"])
            else:
                # Fallback to hash-based
                np.random.seed(hash(text) % (2**32))
                embeddings.append(list(np.random.randn(384).astype(float)))

        return embeddings


def create_embedding_provider(provider_type: str, **kwargs) -> EmbeddingProvider | None:
    """Factory for embedding providers"""
    providers = {
        "openai": OpenAIEmbeddingProvider,
        "ollama": OllamaEmbeddingProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if provider_class:
        return provider_class(**kwargs)
    return None

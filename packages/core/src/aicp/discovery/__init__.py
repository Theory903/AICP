"""
Discovery Module
Module 11 - Capability discovery with semantic search
"""

from aicp.discovery.semantic import (
    EmbeddingResult,
    SemanticSearchResult,
    SemanticDiscovery,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider,
    create_embedding_provider,
)

__all__ = [
    "EmbeddingResult",
    "SemanticSearchResult", 
    "SemanticDiscovery",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "create_embedding_provider",
]
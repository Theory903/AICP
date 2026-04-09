"""
Neo4j GraphRAG Module
Module for knowledge graph construction and retrieval using Neo4j
Integrates with AICP memory (Module 9) and learning (Module 19) systems

Features:
- Knowledge Graph Construction from text/PDF
- Vector similarity search
- Graph traversal retrieval
- Hybrid retrieval combining vector + graph
- Integration with AICP SemanticDiscovery
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RetrievalMode(str, Enum):
    """Retrieval modes for GraphRAG"""
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class VectorIndexType(str, Enum):
    """Vector index types supported"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT = "dot_product"


@dataclass
class GraphEntity:
    """Represents an entity in the knowledge graph"""
    id: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRelation:
    """Represents a relationship between entities"""
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


class KGConstructionError(Exception):
    """Error during knowledge graph construction"""
    pass


class GraphRetrievalError(Exception):
    """Error during graph retrieval"""
    pass


__all__ = [
    "RetrievalMode",
    "VectorIndexType",
    "GraphEntity",
    "GraphRelation",
    "KGConstructionError",
    "GraphRetrievalError",
]

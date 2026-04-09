"""Graph store implementation using Neo4j"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aicp.graphrag import (
    GraphRetrievalError,
    KGConstructionError,
    RetrievalMode,
    VectorIndexType,
)


class Neo4jGraphStore:
    """
    Graph store using Neo4j database.
    Supports knowledge graph construction and retrieval.
    """

    def __init__(
        self,
        uri: str = "neo4j://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
    ):
        self._uri = uri
        self._username = username
        self._password = password
        self._database = database
        self._driver = None
        self._embedder = None

    async def connect(self) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("neo4j driver required: pip install neo4j")
        self._driver = GraphDatabase.driver(
            self._uri,
            auth=(self._username, self._password),
        )

    async def close(self) -> None:
        if self._driver:
            self._driver.close()

    def set_embedder(self, embedder: Any) -> None:
        """Set embedding model for vector operations"""
        self._embedder = embedder

    async def create_vector_index(
        self,
        index_name: str,
        label: str = "Chunk",
        property_name: str = "embedding",
        dimensions: int = 1536,
        similarity_fn: str = "cosine",
    ) -> None:
        if not self._driver:
            raise KGConstructionError("Not connected")

        index_type = VectorIndexType(similarity_fn)
        cypher = f"""CREATE INDEX {index_name} IF NOT EXISTS
FOR (n:{label}) ON (n.{property_name})
OPTIONS {{indexType: '{index_type.value}', dimensions: {dimensions}}}"""
        async with self._driver.session(database=self._database) as session:
            await session.run(cypher)

    async def upsert_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        entity_type: str = "Chunk",
        text_property: str = "text",
        embedding_property: str = "embedding",
    ) -> None:
        if not self._driver:
            raise KGConstructionError("Not connected")

        async with self._driver.session(database=self._database) as session:
            for idx, (node_id, embedding, text) in enumerate(zip(ids, embeddings, texts)):
                cypher = f"""
                MERGE (n:{entity_type} {{id: $id}})
                SET n.{text_property} = $text,
                    n.{embedding_property} = $embedding,
                    n.updated_at = $updated_at
                """
                await session.run(
                    cypher,
                    id=node_id,
                    text=text,
                    embedding=embedding,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )

    async def query_vector(
        self,
        query_embedding: list[float],
        index_name: str,
        label: str = "Chunk",
        embedding_property: str = "embedding",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not self._driver:
            raise KGConstructionError("Not connected")

        cypher = """
        CALL db.index.vector.queryNodes(
            $index_name, $top_k, $embedding
        ) YIELD node, score
        RETURN node.id AS id, node.text AS text, score
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                cypher,
                index_name=index_name,
                top_k=top_k,
                embedding=query_embedding,
            )
            records = await result.data()
            return [
                {"id": r["id"], "text": r["text"], "score": r["score"]}
                for r in records
            ]

    async def add_entity(
        self,
        label: str,
        properties: dict[str, Any],
    ) -> str:
        entity_id = properties.get("id", f"ent_{uuid4().hex[:12]}")
        if not self._driver:
            raise KGConstructionError("Not connected")

        cypher = f"""
        MERGE (e:{label} {{id: $id}})
        SET e += $properties, e.created_at = $created_at
        RETURN e.id AS id
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                cypher,
                id=entity_id,
                properties=properties,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            record = await result.single()
            return record["id"] if record else entity_id

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if not self._driver:
            raise KGConstructionError("Not connected")

        cypher = f"""
        MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
        MERGE (s)-[r:{relation_type}]->(t)
        SET r += $properties, r.created_at = $created_at
        """
        async with self._driver.session(database=self._database) as session:
            await session.run(
                cypher,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                properties=properties or {},
                created_at=datetime.now(timezone.utc).isoformat(),
            )

    async def get_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any] | None:
        if not self._driver:
            raise KGConstructionError("Not connected")

        cypher = "MATCH (e) WHERE e.id = $id RETURN e"
        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, id=entity_id)
            record = await result.single()
            if record:
                return dict(record["e"])
        return None

    async def find_related(
        self,
        entity_id: str,
        relation_types: list[str],
        depth: int = 2,
    ) -> list[dict[str, Any]]:
        if not self._driver:
            raise KGConstructionError("Not connected")

        cypher = f"""
        MATCH (e {{id: $id}})-[r:{"|".join(relation_types)}*1..{depth}]->(related)
        RETURN e.id AS source_id, type(r[0]) AS relation_type,
               related.id AS target_id, related AS properties
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, id=entity_id)
            records = await result.data()
            return records

    async def execute_cypher(
        self,
        cypher: str,
        **params,
    ) -> list[dict[str, Any]]:
        if not self._driver:
            raise KGConstructionError("Not connected")

        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, **params)
            return await result.data()


class Neo4jGraphRetriever:
    """Hybrid retriever combining vector and graph search"""

    def __init__(self, graph_store: Neo4jGraphStore):
        self._store = graph_store

    async def retrieve(
        self,
        query_text: str,
        query_embedding: list[float] | None = None,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 5,
        index_name: str = "vector-index",
    ) -> list[dict[str, Any]]:
        results = []

        if mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            if not query_embedding:
                raise GraphRetrievalError("query_embedding required for vector mode")
            vector_results = await self._store.query_vector(
                query_embedding,
                index_name=index_name,
                top_k=top_k,
            )
            results.extend(vector_results)

        if mode in (RetrievalMode.GRAPH, RetrievalMode.HYBRID):
            entity_type = query_text.split()[0] if query_text else "Entity"
            related = await self._store.find_related(
                entity_type,
                ["KNOWS", "RELATED_TO", "PART_OF"],
                depth=2,
            )
            for r in related:
                results.append({
                    "id": r.get("target_id"),
                    "text": r.get("properties", {}),
                    "score": 0.5,
                    "source": "graph",
                })

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]


__all__ = [
    "Neo4jGraphStore",
    "Neo4jGraphRetriever",
]

"""
Knowledge Graph Construction Pipeline
Constructs knowledge graphs from text using LLM + embeddings
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class KGSchema:
    node_types: list[str]
    relationship_types: list[str]
    patterns: list[tuple[str, str, str]]


@dataclass
class ExtractionResult:
    nodes: list[dict[str, Any]]
    relations: list[dict[str, Any]]


class SimpleKGPipeline:
    """
    Simplified knowledge graph construction from text.
    Uses LLM for entity/relationship extraction.
    """

    def __init__(
        self,
        llm: Any,
        embedder: Any,
        schema: KGSchema | None = None,
    ):
        self._llm = llm
        self._embedder = embedder
        self._schema = schema or KGSchema(
            node_types=["Person", "Organization", "Location", "Concept"],
            relationship_types=["KNOWS", "WORKS_AT", "LOCATED_IN", "RELATED_TO"],
            patterns=[
                ("Person", "KNOWS", "Person"),
                ("Person", "WORKS_AT", "Organization"),
                ("Organization", "LOCATED_IN", "Location"),
                ("Concept", "RELATED_TO", "Concept"),
            ],
        )

    async def run(self, text: str) -> ExtractionResult:
        prompt = self._build_extraction_prompt(text)
        response = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_llm_response(response)

    def _build_extraction_prompt(self, text: str) -> str:
        nodes = ", ".join(self._schema.node_types)
        rels = ", ".join(self._schema.relationship_types)
        return f"""Extract entities and relationships from the following text.

Nodes (entity types): {nodes}
Relationships: {rels}

Return as JSON with 'nodes' and 'relations' keys.
Text: {text[:2000]}
"""

    def _parse_llm_response(self, response: str) -> ExtractionResult:
        import json
        try:
            data = json.loads(response)
            return ExtractionResult(
                nodes=data.get("nodes", []),
                relations=data.get("relations", []),
            )
        except json.JSONDecodeError:
            return ExtractionResult(nodes=[], relations=[])


class Pipeline:
    """
    Full KG builder with configurable extraction and chunking.
    """

    def __init__(
        self,
        llm: Any,
        embedder: Any,
        node_types: list[str],
        relationship_types: list[str],
        chunk_size: int = 1000,
        on_error: str = "IGNORE",
    ):
        self._llm = llm
        self._embedder = embedder
        self._node_types = node_types
        self._relationship_types = relationship_types
        self._chunk_size = chunk_size
        self._on_error = on_error

    async def run_async(self, text: str) -> dict[str, Any]:
        chunks = self._chunk_text(text)
        all_nodes = []
        all_relations = []

        for chunk in chunks:
            try:
                result = await self._extract_from_chunk(chunk)
                all_nodes.extend(result.nodes)
                all_relations.extend(result.relations)
            except Exception:
                if self._on_error == "IGNORE":
                    continue
                raise

        return {
            "nodes": all_nodes,
            "relations": all_relations,
            "chunks_processed": len(chunks),
        }

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self._chunk_size):
            chunks.append(" ".join(words[i : i + self._chunk_size]))
        return chunks

    async def _extract_from_chunk(self, chunk: str) -> ExtractionResult:
        prompt = f"""Extract knowledge graph from this text.

Allowed nodes: {self._node_types}
Allowed relations: {self._relationship_types}

Text: {chunk}

Return JSON: {{"nodes": [{{"id": "...", "type": "...", "properties": {{}}}}], "relations": [{{"source": "...", "target": "...", "type": "..."}}]}}
"""
        response = await self._llm.chat(messages=[{"role": "user", "content": prompt}])
        try:
            import json
            data = json.loads(response)
            return ExtractionResult(
                nodes=data.get("nodes", []),
                relations=data.get("relations", []),
            )
        except Exception:
            return ExtractionResult(nodes=[], relations=[])


__all__ = ["KGSchema", "SimpleKGPipeline", "Pipeline", "ExtractionResult"]

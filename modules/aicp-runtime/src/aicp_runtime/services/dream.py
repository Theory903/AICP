import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class DreamOperation(str, Enum):
    CONSOLIDATE = "consolidate"
    PRUNE = "prune"
    MERGE = "merge"
    ANALYZE = "analyze"


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    SKILL = "skill"
    ENVIRONMENTAL = "environmental"
    ALL = "all"


class ConsolidationMode(str, Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class DreamError(AicpError):
    pass


class DreamNoMemoryError(DreamError):
    pass


@dataclass
class MemoryFragment:
    id: str
    memory_type: str
    content: str
    importance: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsolidationResult:
    operation: str
    memories_processed: int
    memories_removed: int
    memories_merged: int
    tokens_saved: int
    duration_ms: int
    timestamp: datetime


class RetentionPolicy(BaseModel):
    importance_threshold: float = Field(default=0.3, ge=0, le=1)
    recency_weight: float = Field(default=0.4, ge=0, le=1)
    decay_rate: float = Field(default=0.1, ge=0, le=1)


class DreamConfig(BaseModel):
    operation: DreamOperation
    memory_type: MemoryType = Field(default=MemoryType.ALL)
    consolidation_mode: ConsolidationMode = Field(default=ConsolidationMode.BALANCED)
    max_tokens: int = Field(default=50000, ge=1000, le=100000)
    retention_policy: Optional[RetentionPolicy] = None


class DreamService:
    def __init__(self):
        self._memories: dict[str, MemoryFragment] = {}
        self._token_count = 0
        self._consolidation_count = 0

    def _estimate_tokens(self, text: str) -> int:
        return len(text.split()) + (len(text) // 4)

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: float = 0.5,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        memory = MemoryFragment(
            id=memory_id,
            memory_type=memory_type.value,
            content=content,
            importance=importance,
            created_at=now,
            last_accessed=now,
            access_count=1,
            metadata=metadata or {},
        )
        self._memories[memory_id] = memory
        self._token_count += self._estimate_tokens(content)
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[MemoryFragment]:
        if memory_id in self._memories:
            mem = self._memories[memory_id]
            mem.last_accessed = datetime.now(timezone.utc)
            mem.access_count += 1
            return mem
        return None

    def get_all_memories(
        self, memory_type: Optional[MemoryType] = None
    ) -> list[MemoryFragment]:
        if memory_type:
            return [
                m for m in self._memories.values() if m.memory_type == memory_type.value
            ]
        return list(self._memories.values())

    def calculate_importance_score(self, memory: MemoryFragment) -> float:
        recency = (datetime.now(timezone.utc) - memory.last_accessed).total_seconds()
        recency_score = max(0, 1 - (recency / (7 * 24 * 3600)))
        access_score = min(1, memory.access_count / 10)
        return (memory.importance * 0.6) + (recency_score * 0.3) + (access_score * 0.1)

    async def consolidate(
        self,
        memory_type: MemoryType = MemoryType.ALL,
        mode: ConsolidationMode = ConsolidationMode.BALANCED,
    ) -> ConsolidationResult:
        start = time.perf_counter()
        memories_to_process = self.get_all_memories(memory_type)
        removed = 0
        merged = 0
        tokens_before = self._token_count

        if mode == ConsolidationMode.AGGRESSIVE:
            threshold = 0.6
        elif mode == ConsolidationMode.CONSERVATIVE:
            threshold = 0.2
        else:
            threshold = 0.4

        to_remove = []
        for mem in memories_to_process:
            if self.calculate_importance_score(mem) < threshold:
                to_remove.append(mem.id)

        for mem_id in to_remove:
            removed += 1
            self._token_count -= self._estimate_tokens(self._memories[mem_id].content)
            del self._memories[mem_id]

        similar_groups: dict[str, list[MemoryFragment]] = {}
        for mem in memories_to_process:
            if mem.id in to_remove:
                continue
            key = f"{mem.memory_type}_{len(mem.content.split()[:5])}"
            if key not in similar_groups:
                similar_groups[key] = []
            similar_groups[key].append(mem)

        for group in similar_groups.values():
            if len(group) > 1:
                merged += len(group) - 1
                merged_content = " | ".join([m.content for m in group])
                main_mem = group[0]
                main_mem.content = merged_content[:1000]
                for mem in group[1:]:
                    if mem.id in self._memories:
                        self._token_count -= self._estimate_tokens(mem.content)
                        del self._memories[mem.id]

        self._consolidation_count += 1
        duration_ms = int((time.perf_counter() - start) * 1000)

        return ConsolidationResult(
            operation="consolidate",
            memories_processed=len(memories_to_process),
            memories_removed=removed,
            memories_merged=merged,
            tokens_saved=tokens_before - self._token_count,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
        )

    async def prune(
        self,
        memory_type: MemoryType = MemoryType.ALL,
        max_tokens: int = 50000,
    ) -> ConsolidationResult:
        start = time.perf_counter()
        memories_to_process = self.get_all_memories(memory_type)
        removed = 0

        scored_memories = [
            (m, self.calculate_importance_score(m)) for m in memories_to_process
        ]
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        kept_tokens = 0
        to_remove = []

        for mem, score in scored_memories:
            mem_tokens = self._estimate_tokens(mem.content)
            if kept_tokens + mem_tokens > max_tokens:
                to_remove.append(mem)
            else:
                kept_tokens += mem_tokens

        for mem in to_remove:
            removed += 1
            self._token_count -= self._estimate_tokens(mem.content)
            del self._memories[mem.id]

        duration_ms = int((time.perf_counter() - start) * 1000)

        return ConsolidationResult(
            operation="prune",
            memories_processed=len(memories_to_process),
            memories_removed=removed,
            memories_merged=0,
            tokens_saved=0,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
        )

    async def merge(
        self,
        memory_type: MemoryType = MemoryType.ALL,
    ) -> ConsolidationResult:
        return await self.consolidate(memory_type, ConsolidationMode.BALANCED)

    async def analyze(
        self,
        memory_type: MemoryType = MemoryType.ALL,
    ) -> dict[str, Any]:
        memories = self.get_all_memories(memory_type)
        if not memories:
            raise DreamNoMemoryError(f"No memories of type {memory_type.value}")

        total_importance = sum(self.calculate_importance_score(m) for m in memories)
        avg_importance = total_importance / len(memories) if memories else 0

        type_counts: dict[str, int] = {}
        for mem in memories:
            type_counts[mem.memory_type] = type_counts.get(mem.memory_type, 0) + 1

        return {
            "total_memories": len(memories),
            "average_importance": round(avg_importance, 3),
            "total_tokens": self._token_count,
            "memory_type_distribution": type_counts,
            "consolidations_performed": self._consolidation_count,
            "memory_capacity_percent": round((self._token_count / 50000) * 100, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_memories": len(self._memories),
            "total_tokens": self._token_count,
            "consolidation_count": self._consolidation_count,
            "memory_types": list(set(m.memory_type for m in self._memories.values())),
        }

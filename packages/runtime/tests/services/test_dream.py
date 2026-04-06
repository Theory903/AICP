import pytest
from aicp_runtime.services.dream import (
    ConsolidationMode,
    ConsolidationResult,
    DreamConfig,
    DreamOperation,
    DreamService,
    MemoryType,
)


class TestDreamConfig:
    def test_default_config(self):
        config = DreamConfig(operation=DreamOperation.CONSOLIDATE)
        assert config.operation == DreamOperation.CONSOLIDATE
        assert config.memory_type == MemoryType.ALL
        assert config.consolidation_mode == ConsolidationMode.BALANCED

    def test_custom_config(self):
        config = DreamConfig(
            operation= DreamOperation.PRUNE,
            memory_type=MemoryType.EPISODIC,
            consolidation_mode=ConsolidationMode.AGGRESSIVE,
            max_tokens=30000,
        )
        assert config.operation == DreamOperation.PRUNE
        assert config.memory_type == MemoryType.EPISODIC
        assert config.max_tokens == 30000


class TestDreamEnums:
    def test_operation_values(self):
        assert DreamOperation.CONSOLIDATE == "consolidate"
        assert DreamOperation.PRUNE == "prune"
        assert DreamOperation.MERGE == "merge"
        assert DreamOperation.ANALYZE == "analyze"


class TestDreamService:
    def test_init(self):
        service = DreamService()
        assert len(service._memories) == 0
        assert service._token_count == 0

    def test_add_memory(self):
        service = DreamService()
        mem_id = service.add_memory("Test content", MemoryType.WORKING, 0.8)
        assert mem_id.startswith("mem_")
        assert len(service._memories) == 1

    def test_get_memory(self):
        service = DreamService()
        mem_id = service.add_memory("Test", MemoryType.EPISODIC)
        mem = service.get_memory(mem_id)
        assert mem is not None
        assert mem.content == "Test"

    def test_get_memory_not_found(self):
        service = DreamService()
        assert service.get_memory("nonexistent") is None

    def test_get_all_memories_filtered(self):
        service = DreamService()
        service.add_memory("Working 1", MemoryType.WORKING, 0.5)
        service.add_memory("Working 2", MemoryType.WORKING, 0.5)
        service.add_memory("Episodic 1", MemoryType.EPISODIC, 0.5)
        working = service.get_all_memories(MemoryType.WORKING)
        assert len(working) == 2


@pytest.mark.asyncio
class TestDreamOperations:
    async def test_consolidate_balanced(self):
        service = DreamService()
        service.add_memory("Low importance", MemoryType.EPISODIC, 0.2)
        service.add_memory("High importance", MemoryType.EPISODIC, 0.8)
        result = await service.consolidate(MemoryType.EPISODIC, ConsolidationMode.BALANCED)
        assert isinstance(result, ConsolidationResult)
        assert result.operation == "consolidate"

    async def test_consolidate_aggressive(self):
        service = DreamService()
        service.add_memory("Low", MemoryType.EPISODIC, 0.1)
        service.add_memory("Med", MemoryType.EPISODIC, 0.4)
        result = await service.consolidate(MemoryType.EPISODIC, ConsolidationMode.AGGRESSIVE)
        assert result.memories_removed >= 0

    async def test_prune(self):
        service = DreamService()
        service.add_memory("A" * 100, MemoryType.EPISODIC, 0.9)
        service.add_memory("B" * 100, MemoryType.EPISODIC, 0.9)
        result = await service.prune(MemoryType.EPISODIC, max_tokens=50)
        assert result.memories_removed >= 0

    async def test_merge(self):
        service = DreamService()
        service.add_memory("Test 1", MemoryType.EPISODIC)
        result = await service.merge(MemoryType.EPISODIC)
        assert result.operation == "consolidate"

    async def test_analyze(self):
        service = DreamService()
        service.add_memory("Test", MemoryType.EPISODIC, 0.5)
        analysis = await service.analyze(MemoryType.EPISODIC)
        assert "total_memories" in analysis
        assert analysis["total_memories"] == 1


class TestDreamStats:
    def test_get_stats(self):
        service = DreamService()
        service.add_memory("Test", MemoryType.WORKING)
        stats = service.get_stats()
        assert stats["total_memories"] == 1
        assert "total_tokens" in stats

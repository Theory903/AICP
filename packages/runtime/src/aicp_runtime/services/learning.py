from __future__ import annotations

from typing import Any, Optional
from aicp.learning.learning import (
    LearningService as CoreLearningService,
    DomainPack,
    Benchmark,
    BenchmarkResult,
    DomainCategory,
)


class LearningService:
    """Runtime service for learning, domain packs, and benchmarks."""

    def __init__(self, core_learning_service: CoreLearningService | None = None):
        self._core = core_learning_service or CoreLearningService()

    def add_domain_pack(self, pack: DomainPack) -> None:
        self._core.add_domain_pack(pack)

    def get_domain_pack(self, pack_id: str) -> Optional[DomainPack]:
        return self._core.get_domain_pack(pack_id)

    def get_domain_packs(self, category: Optional[DomainCategory] = None) -> list[DomainPack]:
        return self._core.get_domain_packs(category)

    def add_benchmark(self, benchmark: Benchmark) -> None:
        self._core.add_benchmark(benchmark)

    def get_benchmark(self, benchmark_id: str) -> Optional[Benchmark]:
        return self._core.get_benchmark(benchmark_id)

    def get_all_benchmarks(self) -> list[Benchmark]:
        return self._core.get_all_benchmarks()

    def record_benchmark_result(self, result: BenchmarkResult) -> None:
        self._core.record_benchmark_result(result)

    def get_benchmark_results(self, benchmark_id: Optional[str] = None) -> list[BenchmarkResult]:
        return self._core.get_benchmark_results(benchmark_id)

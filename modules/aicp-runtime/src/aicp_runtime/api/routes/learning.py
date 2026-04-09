from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from aicp.learning.domains import DomainPack, Benchmark, BenchmarkResult, DomainCategory
from aicp_runtime.services.learning import LearningService


class DomainPackView(BaseModel):
    id: str
    name: str
    description: str
    category: str
    version: str
    capabilities_count: int


class BenchmarkView(BaseModel):
    id: str
    name: str
    description: str
    benchmark_type: str
    metric_name: str
    unit: str


def build_learning_router(learning_service: LearningService) -> APIRouter:
    router = APIRouter(prefix="/v1/learning", tags=["learning"])

    @router.get("/domains", response_model=List[DomainPackView])
    async def list_domain_packs(
        category: Optional[DomainCategory] = Query(None),
    ) -> List[DomainPackView]:
        packs = learning_service.get_domain_packs(category)
        return [
            DomainPackView(
                id=p.id,
                name=p.name,
                description=p.description,
                category=p.category.value,
                version=p.version,
                capabilities_count=len(p.capabilities),
            )
            for p in packs
        ]

    @router.get("/domains/{pack_id}", response_model=DomainPack)
    async def get_domain_pack(pack_id: str) -> DomainPack:
        pack = learning_service.get_domain_pack(pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Domain pack not found")
        return pack

    @router.get("/benchmarks", response_model=List[BenchmarkView])
    async def list_benchmarks() -> List[BenchmarkView]:
        benchmarks = learning_service.get_all_benchmarks()
        return [
            BenchmarkView(
                id=b.id,
                name=b.name,
                description=b.description,
                benchmark_type=b.benchmark_type.value,
                metric_name=b.metric_name,
                unit=b.unit,
            )
            for b in benchmarks
        ]

    @router.get("/benchmarks/{benchmark_id}", response_model=Benchmark)
    async def get_benchmark(benchmark_id: str) -> Benchmark:
        benchmark = learning_service.get_benchmark(benchmark_id)
        if not benchmark:
            raise HTTPException(status_code=404, detail="Benchmark not found")
        return benchmark

    @router.post(
        "/benchmarks/results",
        response_model=BenchmarkResult,
        status_code=status.HTTP_201_CREATED,
    )
    async def record_benchmark_result(result: BenchmarkResult) -> BenchmarkResult:
        learning_service.record_benchmark_result(result)
        return result

    @router.get(
        "/benchmarks/{benchmark_id}/results", response_model=List[BenchmarkResult]
    )
    async def get_benchmark_results(benchmark_id: str) -> List[BenchmarkResult]:
        return learning_service.get_benchmark_results(benchmark_id)

    return router

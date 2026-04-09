import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DomainCategory(str, Enum):
    ECOMMERCE = "ecommerce"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    DATA_ANALYTICS = "data_analytics"
    DevOps = "devops"
    SECURITY = "security"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"


class BenchmarkType(str, Enum):
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    ACCURACY = "accuracy"
    THROUGHPUT = "throughput"
    LATENCY = "latency"


class DomainCapability(BaseModel):
    name: str
    description: str
    kind: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "low"


class DomainPack(BaseModel):
    id: str = Field(default_factory=lambda: f"dp_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    category: DomainCategory
    version: str = "1.0.0"
    capabilities: list[DomainCapability] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Benchmark(BaseModel):
    id: str = Field(default_factory=lambda: f"bench_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    benchmark_type: BenchmarkType
    metric_name: str
    unit: str
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    pass_threshold: float
    timeout_seconds: int = 60
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSuite(BaseModel):
    id: str = Field(default_factory=lambda: f"bs_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    benchmarks: list[Benchmark] = Field(default_factory=list)
    version: str = "1.0.0"


class BenchmarkRun(BaseModel):
    id: str = Field(default_factory=lambda: f"br_{uuid.uuid4().hex[:8]}")
    benchmark_id: str
    test_case: dict[str, Any]
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None
    passed: bool = False
    value: float | None = None
    error: str | None = None


class BenchmarkReport(BaseModel):
    id: str = Field(default_factory=lambda: f"report_{uuid.uuid4().hex[:8]}")
    suite_name: str
    run_id: str
    benchmark_results: list[BenchmarkRun] = Field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    total_duration_ms: float = 0.0
    summary: str = ""


class DomainPackRegistry:
    def __init__(self):
        self._packs: dict[str, DomainPack] = {}
        self._benchmarks: dict[str, Benchmark] = {}
        self._suites: dict[str, BenchmarkSuite] = {}
        self._reports: list[BenchmarkReport] = []

    def register_pack(self, pack: DomainPack) -> None:
        self._packs[pack.id] = pack

    def get_pack(self, pack_id: str) -> DomainPack | None:
        return self._packs.get(pack_id)

    def get_packs_by_category(self, category: DomainCategory) -> list[DomainPack]:
        return [p for p in self._packs.values() if p.category == category]

    def get_all_packs(self) -> list[DomainPack]:
        return list(self._packs.values())

    def register_benchmark(self, benchmark: Benchmark) -> None:
        self._benchmarks[benchmark.id] = benchmark

    def get_benchmark(self, benchmark_id: str) -> Benchmark | None:
        return self._benchmarks.get(benchmark_id)

    def get_all_benchmarks(self) -> list[Benchmark]:
        return list(self._benchmarks.values())

    def register_suite(self, suite: BenchmarkSuite) -> None:
        self._suites[suite.id] = suite
        for bench in suite.benchmarks:
            self._benchmarks[bench.id] = bench

    def get_suite(self, suite_id: str) -> BenchmarkSuite | None:
        return self._suites.get(suite_id)

    def get_all_suites(self) -> list[BenchmarkSuite]:
        return list(self._suites.values())

    def run_suite(self, suite_id: str, test_inputs: list[dict[str, Any]]) -> BenchmarkReport:
        suite = self._suites.get(suite_id)
        if not suite:
            raise ValueError(f"Suite {suite_id} not found")

        results = []
        passed = 0
        failed = 0
        total_duration = 0.0

        for benchmark in suite.benchmarks:
            for test_input in test_inputs:
                run = BenchmarkRun(
                    benchmark_id=benchmark.id,
                    test_case=test_input
                )

                value = test_input.get("expected_value", 100.0)
                passed_test = value >= benchmark.pass_threshold

                run.passed = passed_test
                run.value = value
                run.completed_at = datetime.utcnow().isoformat()

                if passed_test:
                    passed += 1
                else:
                    failed += 1

                results.append(run)
                total_duration += test_input.get("duration_ms", 10.0)

        report = BenchmarkReport(
            suite_name=suite.name,
            run_id=str(uuid.uuid4()),
            benchmark_results=results,
            passed_count=passed,
            failed_count=failed,
            total_duration_ms=total_duration,
            summary=f"{passed}/{passed+failed} benchmarks passed"
        )

        self._reports.append(report)
        return report

    def get_reports(self, limit: int = 10) -> list[BenchmarkReport]:
        return self._reports[-limit:]


class EcommercePack(DomainPack):
    @staticmethod
    def create() -> DomainPack:
        return DomainPack(
            name="E-Commerce",
            description="Pre-built capabilities for e-commerce operations",
            category=DomainCategory.ECOMMERCE,
            capabilities=[
                DomainCapability(
                    name="product.search",
                    description="Search products by query",
                    kind="query",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                    tags=["product", "search"],
                    risk_level="low"
                ),
                DomainCapability(
                    name="cart.add",
                    description="Add item to shopping cart",
                    kind="action",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                        },
                    },
                    output_schema={"type": "object", "properties": {"cart_id": {"type": "string"}}},
                    tags=["cart", "shopping"],
                    risk_level="medium"
                ),
                DomainCapability(
                    name="checkout.process",
                    description="Process checkout",
                    kind="action",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "cart_id": {"type": "string"},
                            "payment_method": {"type": "string"},
                        },
                    },
                    output_schema={"type": "object", "properties": {"order_id": {"type": "string"}}},
                    tags=["checkout", "payment"],
                    risk_level="high"
                ),
            ]
        )


class ProductivityPack(DomainPack):
    @staticmethod
    def create() -> DomainPack:
        return DomainPack(
            name="Productivity",
            description="Pre-built capabilities for productivity workflows",
            category=DomainCategory.PRODUCTIVITY,
            capabilities=[
                DomainCapability(
                    name="notes.create",
                    description="Create a new note",
                    kind="action",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                        },
                    },
                    output_schema={"type": "object", "properties": {"note_id": {"type": "string"}}},
                    tags=["notes", "create"],
                    risk_level="low"
                ),
                DomainCapability(
                    name="tasks.list",
                    description="List all tasks",
                    kind="query",
                    input_schema={"type": "object", "properties": {}},
                    output_schema={"type": "object", "properties": {"tasks": {"type": "array"}}},
                    tags=["tasks", "list"],
                    risk_level="low"
                ),
            ]
        )


class DevOpsPack(DomainPack):
    @staticmethod
    def create() -> DomainPack:
        return DomainPack(
            name="DevOps",
            description="Pre-built capabilities for DevOps operations",
            category=DomainCategory.DevOps,
            capabilities=[
                DomainCapability(
                    name="deploy.run",
                    description="Run a deployment",
                    kind="action",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "environment": {"type": "string"},
                            "version": {"type": "string"},
                        },
                    },
                    output_schema={"type": "object", "properties": {"deployment_id": {"type": "string"}}},
                    tags=["deploy", "ci/cd"],
                    risk_level="high"
                ),
                DomainCapability(
                    name="logs.query",
                    description="Query application logs",
                    kind="query",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "service": {"type": "string"},
                            "level": {"type": "string"},
                        },
                    },
                    output_schema={"type": "object", "properties": {"logs": {"type": "array"}}},
                    tags=["logs", "monitoring"],
                    risk_level="low"
                ),
            ]
        )


class DefaultBenchmarkSuite(BenchmarkSuite):
    @staticmethod
    def create() -> BenchmarkSuite:
        return BenchmarkSuite(
            name="AICP Default Suite",
            description="Standard benchmark suite for AICP capabilities",
            benchmarks=[
                Benchmark(
                    name="capability_latency",
                    description="Measure capability execution latency",
                    benchmark_type=BenchmarkType.LATENCY,
                    metric_name="execution_time_ms",
                    unit="ms",
                    pass_threshold=100.0,
                    test_cases=[{"name": "fast_cap", "expected_value": 50.0}],
                ),
                Benchmark(
                    name="capability_throughput",
                    description="Measure capability throughput",
                    benchmark_type=BenchmarkType.THROUGHPUT,
                    metric_name="requests_per_second",
                    unit="req/s",
                    pass_threshold=1000.0,
                    test_cases=[{"name": "high_throughput", "expected_value": 1500.0}],
                ),
                Benchmark(
                    name="workflow_reliability",
                    description="Measure workflow success rate",
                    benchmark_type=BenchmarkType.RELIABILITY,
                    metric_name="success_rate",
                    unit="%",
                    pass_threshold=95.0,
                    test_cases=[{"name": "reliable_wf", "expected_value": 98.0}],
                ),
            ]
        )

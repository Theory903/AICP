"""Benchmarks for AICP core operations.

These tests measure performance of core AICP operations.
"""

import time

import pytest

from aicp import (
    AicpExecutor,
    AicpRegistry,
    Capability,
    CapabilityKind,
    Policy,
    PolicyEffect,
    PolicySubject,
)
from aicp.implementations import DefaultPolicyEngine, InMemoryCapabilityRepository
from aicp.interfaces import ExecutionStatus


class BenchmarkResults:
    """Container for benchmark results."""

    def __init__(self):
        self.results = {}

    def record(self, name: str, duration_ms: float):
        self.results[name] = duration_ms

    def report(self) -> str:
        lines = ["Benchmark Results:", "=" * 40]
        for name, duration in sorted(self.results.items()):
            lines.append(f"  {name}: {duration:.2f}ms")
        return "\n".join(lines)


@pytest.fixture(scope="session")
def benchmark_results():
    return BenchmarkResults()


@pytest.fixture
def sample_capabilities():
    """Create 100 sample capabilities for benchmarking."""
    return [
        Capability(
            name=f"test.action_{i}",
            description=f"Test action {i}",
            kind=CapabilityKind.ACTION,
        )
        for i in range(100)
    ]


class TestCapabilityBenchmarks:
    """Benchmarks for capability operations."""

    def test_capability_creation(self, benchmark_results):
        """Benchmark capability creation."""
        start = time.perf_counter()

        for i in range(1000):
            cap = Capability(
                name=f"test.action_{i}",
                description=f"Test action {i}",
                kind=CapabilityKind.ACTION,
            )

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("capability_creation_1000", duration_ms)

        assert duration_ms < 500, f"Capability creation too slow: {duration_ms}ms"

    def test_capability_serialization(self, benchmark_results):
        """Benchmark capability JSON serialization."""
        cap = Capability(
            name="test.action",
            description="Test action",
            kind=CapabilityKind.ACTION,
        )

        start = time.perf_counter()
        for _ in range(1000):
            cap.model_dump_json()

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("capability_serialization_1000", duration_ms)

        assert duration_ms < 1000, f"Serialization too slow: {duration_ms}ms"


class TestRegistryBenchmarks:
    """Benchmarks for registry operations."""

    def test_registry_discovery(self, benchmark_results, sample_capabilities):
        """Benchmark discovery of 100 capabilities."""
        registry = AicpRegistry()
        for cap in sample_capabilities:
            registry.register_capability(cap)

        start = time.perf_counter()
        for _ in range(100):
            discovery = registry.discovery_response()

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("registry_discovery_100", duration_ms)

        assert duration_ms < 500, f"Discovery too slow: {duration_ms}ms"

    def test_registry_lookup(self, benchmark_results, sample_capabilities):
        """Benchmark single capability lookup."""
        registry = AicpRegistry()
        for cap in sample_capabilities:
            registry.register_capability(cap)

        start = time.perf_counter()
        for i in range(1000):
            cap = registry.get_capability(f"test.action_{i % 100}")

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("registry_lookup_1000", duration_ms)

        assert duration_ms < 100, f"Lookup too slow: {duration_ms}ms"

    def test_registry_list(self, benchmark_results, sample_capabilities):
        """Benchmark listing all capabilities."""
        registry = AicpRegistry()
        for cap in sample_capabilities:
            registry.register_capability(cap)

        start = time.perf_counter()
        for _ in range(1000):
            caps = registry.list_capabilities()

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("registry_list_1000", duration_ms)

        assert duration_ms < 200, f"List too slow: {duration_ms}ms"


class TestPolicyBenchmarks:
    """Benchmarks for policy operations."""

    def test_policy_creation(self, benchmark_results):
        """Benchmark policy creation."""
        start = time.perf_counter()

        for i in range(1000):
            policy = Policy(
                name=f"test.policy_{i}",
                description=f"Test policy {i}",
                effect=PolicyEffect.ALLOW,
                subject=PolicySubject(capability_name="test.action"),
            )

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("policy_creation_1000", duration_ms)

        assert duration_ms < 500, f"Policy creation too slow: {duration_ms}ms"

    @pytest.mark.asyncio
    async def test_policy_evaluation(self, benchmark_results):
        """Benchmark policy evaluation."""
        engine = DefaultPolicyEngine()

        # Add 10 policies
        for i in range(10):
            policy = Policy(
                name=f"test.policy_{i}",
                description=f"Test policy {i}",
                effect=PolicyEffect.ALLOW,
                subject=PolicySubject(capability_name="test.action"),
            )
            await engine.add_policy(policy)

        start = time.perf_counter()
        for _ in range(1000):
            decision = await engine.evaluate("test.action", {}, {})

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("policy_evaluation_1000", duration_ms)

        assert duration_ms < 1000, f"Policy evaluation too slow: {duration_ms}ms"


class TestExecutorBenchmarks:
    """Benchmarks for executor operations."""

    @pytest.mark.asyncio
    async def test_executor_success_case(self, benchmark_results):
        """Benchmark executor with successful execution."""
        repo = InMemoryCapabilityRepository()
        executor = AicpExecutor(repo)

        # Register a capability
        cap = Capability(
            name="test.action",
            description="Test action",
            kind=CapabilityKind.ACTION,
        )
        repo.add_capability(cap)

        # Override execute to be fast
        async def mock_execute(name, args, ctx):
            return {"result": "success"}

        repo.execute = mock_execute

        start = time.perf_counter()
        for _ in range(1000):
            result = await executor.execute("test.action", {})

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("executor_success_1000", duration_ms)

        assert duration_ms < 2000, f"Executor too slow: {duration_ms}ms"
        assert all(r.status == ExecutionStatus.SUCCESS for r in [result])

    @pytest.mark.asyncio
    async def test_executor_not_found(self, benchmark_results):
        """Benchmark executor with not found error."""
        repo = InMemoryCapabilityRepository()
        executor = AicpExecutor(repo)

        start = time.perf_counter()
        for _ in range(1000):
            result = await executor.execute("nonexistent", {})

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("executor_not_found_1000", duration_ms)

        assert duration_ms < 500, f"Executor error case too slow: {duration_ms}ms"


class TestWorkflowBenchmarks:
    """Benchmarks for workflow operations."""

    @pytest.mark.asyncio
    async def test_workflow_creation(self, benchmark_results):
        """Benchmark workflow creation."""
        from aicp.implementations import DefaultWorkflowRuntime

        repo = InMemoryCapabilityRepository()
        runtime = DefaultWorkflowRuntime(repo)

        start = time.perf_counter()
        for i in range(100):
            workflow = await runtime.create_workflow(
                name=f"workflow_{i}",
                description=f"Test workflow {i}",
                steps=[
                    {"capability_name": "test.action", "arguments": {}},
                ],
            )

        duration_ms = (time.perf_counter() - start) * 1000
        benchmark_results.record("workflow_creation_100", duration_ms)

        assert duration_ms < 500, f"Workflow creation too slow: {duration_ms}ms"


def test_benchmark_summary(benchmark_results):
    """Verify benchmark results meet minimum performance thresholds."""
    # Ensure results were recorded
    assert len(benchmark_results.results) > 0, "No benchmark results recorded"

    # Verify each operation is under reasonable threshold (5 seconds)
    for name, duration_ms in benchmark_results.results.items():
        assert duration_ms < 5000, f"Benchmark {name} exceeded 5s threshold: {duration_ms}ms"

    # Critical operations must meet stricter thresholds
    critical_ops = [
        "registry_lookup_1000",
        "capability_creation_1000",
    ]
    for op in critical_ops:
        if op in benchmark_results.results:
            assert benchmark_results.results[op] < 500, f"Critical op {op} too slow: {benchmark_results.results[op]}ms"

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
    DEVOPS = "devops"
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
    id: str = Field(default_factory=lambda: f"bm_{uuid.uuid4().hex[:8]}")
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
    id: str = Field(default_factory=lambda: f"bms_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    benchmarks: list[Benchmark] = Field(default_factory=list)
    version: str = "1.0.0"


class BenchmarkResult(BaseModel):
    id: str = Field(default_factory=lambda: f"br_{uuid.uuid4().hex[:8]}")
    benchmark_id: str
    metric_name: str
    value: float
    unit: str
    status: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

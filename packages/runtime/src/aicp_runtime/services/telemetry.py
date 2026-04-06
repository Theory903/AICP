import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor, SpanExporter
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Span, Status, StatusCode, TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.logging import LoggerProvider
from opentelemetry._logs import set_logger_provider
from pydantic import BaseModel, Field

from aicp.errors import AicpError


class TelemetryExporter(str, Enum):
    CONSOLE = "console"
    OTLP = "otlp"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    PROMETHEUS = "prometheus"


class TelemetryError(AicpError):
    pass


class TelemetryNotConfiguredError(TelemetryError):
    pass


class SpanContext:
    def __init__(self, span: Span):
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def set_status(self, code: StatusCode, message: str = "") -> None:
        self._span.set_status(Status(code, message))

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self._span.add_event(name, attributes or {})

    def end(self) -> None:
        self._span.end()


@dataclass
class MetricValue:
    name: str
    value: float
    unit: str
    attributes: dict[str, Any]
    timestamp: datetime


class TelemetryConfig(BaseModel):
    enabled: bool = True
    service_name: str = "aicp"
    exporter: TelemetryExporter = Field(default=TelemetryExporter.CONSOLE)
    endpoint: Optional[str] = None
    sample_rate: float = Field(default=1.0, ge=0, le=1)
    traces_enabled: bool = True
    metrics_enabled: bool = True
    logs_enabled: bool = True
    log_level: str = Field(default="info", pattern="^(debug|info|warn|error)$")


class TelemetryService:
    _instance: Optional["TelemetryService"] = None

    def __init__(self):
        self._enabled = False
        self._tracer: Optional[Any] = None
        self._meter: Optional[Any] = None
        self._logger: Optional[logging.Logger] = None
        self._span_processors: list[SpanProcessor] = []
        self._active_spans: int = 0
        self._metrics: dict[str, list[MetricValue]] = {}
        self._trace_counts: dict[str, int] = {}
        self._error_counts: dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> "TelemetryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self, config: TelemetryConfig) -> None:
        if not config.enabled:
            self._enabled = False
            return

        self._enabled = True

        resource = Resource.create({"service.name": config.service_name})
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer(__name__)

        if config.exporter == TelemetryExporter.CONSOLE:
            exporter = ConsoleSpanExporter()
            processor = SimpleSpanProcessor(exporter)
            tracer_provider.add_span_processor(processor)

        try:
            from opentelemetry.sdk.metrics import Counter, UpDownCounter

            meter_provider = MeterProvider()
            self._meter = meter_provider.get_meter(__name__)
        except ImportError:
            pass

        log_level = getattr(logging, config.log_level.upper())
        logging.basicConfig(level=log_level)
        self._logger = logging.getLogger("aicp.telemetry")

    def is_enabled(self) -> bool:
        return self._enabled

    @asynccontextmanager
    async def span(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
    ):
        if not self._enabled or not self._tracer:
            yield SpanContext(None) if False else None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            self._active_spans += 1
            ctx = SpanContext(span)
            try:
                yield ctx
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self._record_error(name)
                raise
            finally:
                self._active_spans -= 1
                self._record_trace(name)

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        attributes: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self._enabled:
            return

        metric = MetricValue(
            name=name,
            value=value,
            unit=unit,
            attributes=attributes or {},
            timestamp=datetime.now(timezone.utc),
        )

        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(metric)

    def record_trace(self, name: str) -> None:
        self._trace_counts[name] = self._trace_counts.get(name, 0) + 1

    def record_error(self, name: str) -> None:
        self._error_counts[name] = self._error_counts.get(name, 0) + 1

    def get_stats(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "active_spans": self._active_spans,
            "trace_counts": self._trace_counts.copy(),
            "error_counts": self._error_counts.copy(),
            "metrics_recorded": {k: len(v) for k, v in self._metrics.items()},
        }

    def reset_stats(self) -> None:
        self._trace_counts.clear()
        self._error_counts.clear()
        self._metrics.clear()


class Tracing:
    @staticmethod
    def trace(name: str):
        def decorator(func: Callable[..., Awaitable[Any]]):
            async def wrapper(*args, **kwargs):
                service = TelemetryService.get_instance()
                async with service.span(name):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def timed(name: str):
        def decorator(func: Callable[..., Awaitable[Any]]):
            async def wrapper(*args, **kwargs):
                service = TelemetryService.get_instance()
                start = time.perf_counter()
                async with service.span(f"{name}.execution"):
                    result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                service.record_metric(f"{name}.duration_ms", duration_ms, "ms")
                return result
            return wrapper
        return decorator

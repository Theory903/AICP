"""Observability: structured logging, metrics, and tracing.

Provides production-grade observability for AICP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sys
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(slots=True)
class LogEntry:
    """Structured log entry."""

    timestamp: str
    level: str
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    tenant_id: str | None = None
    service: str = "aicp"
    metadata: dict[str, Any] = field(default_factory=dict)

    def model_dump(self, exclude_none: bool = False) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        data = asdict(self)
        if exclude_none:
            return {key: value for key, value in data.items() if value is not None}
        return data


class StructuredLogger:
    """Structured JSON logger for AICP.

    Outputs JSON logs suitable for log aggregation.
    """

    def __init__(
        self,
        name: str = "aicp",
        level: str = "INFO",
        output: str = "json",
        service: str = "aicp",
    ) -> None:
        self.name = name
        self.output = output
        self.service = service
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def _utc_now(self) -> str:
        """Return RFC3339-ish UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry."""
        if self.output == "json":
            return json.dumps(entry.model_dump(exclude_none=True), default=str, sort_keys=True)
        return (
            f"[{entry.timestamp}] "
            f"{entry.level.upper()} "
            f"[trace_id={entry.trace_id or '-'} span_id={entry.span_id or '-'}] "
            f"{entry.message}"
        )

    def _log(self, level: LogLevel | str, message: str, **metadata: Any) -> None:
        """Log a structured entry."""
        normalized_level = level.value if isinstance(level, LogLevel) else level.lower()

        entry = LogEntry(
            timestamp=self._utc_now(),
            level=normalized_level,
            message=message,
            trace_id=trace_id_var.get(),
            span_id=span_id_var.get(),
            service=self.service,
            tenant_id=metadata.pop("tenant_id", None),
            metadata=metadata,
        )
        self._logger.log(
            getattr(logging, normalized_level.upper(), logging.INFO),
            self._format_entry(entry),
        )

    def debug(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.DEBUG, message, **metadata)

    def info(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.INFO, message, **metadata)

    def warning(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.WARNING, message, **metadata)

    def error(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.ERROR, message, **metadata)

    def critical(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.CRITICAL, message, **metadata)


_loggers: dict[tuple[str, str, str, str], StructuredLogger] = {}


def get_logger(
    name: str = "aicp",
    level: str = "INFO",
    output: str = "json",
    service: str = "aicp",
) -> StructuredLogger:
    """Get cached structured logger instance."""
    key = (name, level.upper(), output, service)
    if key not in _loggers:
        _loggers[key] = StructuredLogger(
            name=name,
            level=level,
            output=output,
            service=service,
        )
    return _loggers[key]


class MetricsCollector:
    """Simple metrics collector for Prometheus-style output.

    Supports counters, gauges, and summary-like histogram export.
    """

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._lock = Lock()

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram value."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        """Create metric key with labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def to_prometheus(self) -> str:
        """Export metrics in a Prometheus-style text format."""
        lines: list[str] = []

        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = {k: list(v) for k, v in self._histograms.items()}

        for key, value in counters.items():
            metric_name = key.split("{", 1)[0]
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{key} {value}")

        for key, value in gauges.items():
            metric_name = key.split("{", 1)[0]
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{key} {value}")

        for key, values in histograms.items():
            metric_name = key.split("{", 1)[0]
            lines.append(f"# TYPE {metric_name} summary")
            count = len(values)
            total = sum(values)
            lines.append(f"{metric_name}_count {count}")
            lines.append(f"{metric_name}_sum {total}")
            if count > 0:
                lines.append(f"{metric_name}_avg {total / count}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


_global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    return _global_metrics


class Tracer:
    """Simple distributed tracer.

    Creates trace spans for request tracking.
    """

    def __init__(self, service_name: str = "aicp") -> None:
        self.service_name = service_name
        self._spans: list[dict[str, Any]] = []
        self._lock = Lock()

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
    ) -> "Span":
        """Start a new span."""
        return Span(
            name=name,
            tracer=self,
            trace_id=trace_id,
            parent_id=parent_id,
        )

    def record_span(self, span_data: dict[str, Any]) -> None:
        """Store a finished span."""
        with self._lock:
            self._spans.append(span_data)

    def get_spans(self) -> list[dict[str, Any]]:
        """Return a copy of collected spans."""
        with self._lock:
            return list(self._spans)

    def clear_spans(self) -> None:
        """Clear recorded spans."""
        with self._lock:
            self._spans.clear()

    def extract_trace(self, headers: dict[str, str]) -> tuple[str | None, str | None]:
        """Extract trace info from HTTP headers."""
        trace_id = headers.get("X-Trace-ID")
        parent_span_id = headers.get("X-Span-ID")
        return trace_id, parent_span_id

    def inject_trace(self, headers: dict[str, str], trace_id: str, span_id: str) -> None:
        """Inject trace info into HTTP headers."""
        headers["X-Trace-ID"] = trace_id
        headers["X-Span-ID"] = span_id


class Span:
    """Represents a trace span."""

    def __init__(
        self,
        name: str,
        tracer: Tracer,
        trace_id: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        self.name = name
        self.tracer = tracer
        self.trace_id = trace_id or secrets.token_hex(16)
        self.span_id = secrets.token_hex(8)
        self.parent_id = parent_id
        self._started_at_perf = time.perf_counter()
        self._started_at_unix = time.time()
        self._ended = False
        self._attributes: dict[str, Any] = {}
        self._trace_token = None
        self._span_token = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self._attributes[key] = value

    def end(self) -> dict[str, Any]:
        """End span and return span data."""
        if self._ended:
            raise RuntimeError(f"Span '{self.name}' already ended")

        ended_at_unix = time.time()
        duration_ms = (time.perf_counter() - self._started_at_perf) * 1000.0
        self._ended = True

        span_data = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "service": self.tracer.service_name,
            "start_time": self._started_at_unix,
            "end_time": ended_at_unix,
            "duration_ms": duration_ms,
            "attributes": dict(self._attributes),
        }

        self.tracer.record_span(span_data)

        if self._span_token is not None:
            span_id_var.reset(self._span_token)
            self._span_token = None
        if self._trace_token is not None:
            trace_id_var.reset(self._trace_token)
            self._trace_token = None

        return span_data

    def __enter__(self) -> "Span":
        self._trace_token = trace_id_var.set(self.trace_id)
        self._span_token = span_id_var.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc is not None:
            self.set_attribute("error", str(exc))
            self.set_attribute("error_type", getattr(exc_type, "__name__", "Exception"))
        if not self._ended:
            self.end()


_tracers: dict[str, Tracer] = {}


def get_tracer(service_name: str = "aicp") -> Tracer:
    """Get cached tracer instance."""
    if service_name not in _tracers:
        _tracers[service_name] = Tracer(service_name)
    return _tracers[service_name]


class HealthCheck:
    """Health check registry and runner."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[..., Any] | Callable[..., Awaitable[Any]]] = {}

    def register(
        self,
        name: str,
        check: Callable[..., Any] | Callable[..., Awaitable[Any]],
    ) -> None:
        """Register a health check."""
        if not name.strip():
            raise ValueError("Health check name cannot be empty")
        self._checks[name] = check

    async def check(self) -> dict[str, Any]:
        """Run all health checks."""
        results: dict[str, Any] = {}
        overall_healthy = True

        for name, check in self._checks.items():
            try:
                result = check()
                if asyncio.iscoroutine(result):
                    result = await result

                results[name] = {
                    "status": "healthy",
                    "result": result,
                }
            except Exception as exc:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(exc),
                }
                overall_healthy = False

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "checks": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
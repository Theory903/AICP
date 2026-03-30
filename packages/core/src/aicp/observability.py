"""Observability: structured logging, metrics, and tracing.

Provides production-grade observability for AICP.
"""

import asyncio
import json
import logging
import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
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


class StructuredLogger:
    """Structured JSON logger for AICP.

    Outputs JSON logs suitable for log aggregation.
    """

    def __init__(
        self,
        name: str = "aicp",
        level: str = "INFO",
        output: str = "json",
    ):
        self.name = name
        self.output = output
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper()))

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry."""
        if self.output == "json":
            return json.dumps(entry.model_dump(exclude_none=True))
        return f"[{entry.timestamp}] {entry.level.upper()}: {entry.message}"

    def _log(self, level: str, message: str, **metadata) -> None:
        """Log a structured entry."""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            message=message,
            trace_id=trace_id_var.get(),
            metadata=metadata,
        )
        self._logger.log(getattr(logging, level.upper()), self._format_entry(entry))

    def debug(self, message: str, **metadata) -> None:
        self._log("debug", message, **metadata)

    def info(self, message: str, **metadata) -> None:
        self._log("info", message, **metadata)

    def warning(self, message: str, **metadata) -> None:
        self._log("warning", message, **metadata)

    def error(self, message: str, **metadata) -> None:
        self._log("error", message, **metadata)

    def critical(self, message: str, **metadata) -> None:
        self._log("critical", message, **metadata)


def get_logger(name: str = "aicp") -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name)


class MetricsCollector:
    """Simple metrics collector for Prometheus-compatible output.

    Supports counters, gauges, and histograms.
    """

    def __init__(self):
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram value."""
        key = self._make_key(name, labels)
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
        """Export metrics in Prometheus format."""
        lines = []

        for key, value in self._counters.items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")

        for key, value in self._gauges.items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")

        for key, values in self._histograms.items():
            lines.append(f"# TYPE {key} histogram")
            count = len(values)
            total = sum(values)
            lines.append(f"{key}_count {count}")
            lines.append(f"{key}_sum {total}")
            if count > 0:
                lines.append(f"{key}_avg {total / count}")

        return "\n".join(lines)


_global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    return _global_metrics


class Tracer:
    """Simple distributed tracer.

    Creates trace spans for request tracking.
    """

    def __init__(self, service_name: str = "aicp"):
        self.service_name = service_name
        self._spans: list[dict[str, Any]] = []

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

    def extract_trace(self, headers: dict[str, str]) -> tuple[str | None, str | None]:
        """Extract trace info from HTTP headers."""
        trace_id = headers.get("X-Trace-ID")
        span_id = headers.get("X-Span-ID")
        return trace_id, span_id

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
    ):
        import secrets
        self.name = name
        self.tracer = tracer
        self.trace_id = trace_id or secrets.token_hex(16)
        self.span_id = secrets.token_hex(8)
        self.parent_id = parent_id
        self._start_time = time.time()
        self._end_time: float | None = None
        self._attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self._attributes[key] = value

    def end(self) -> dict[str, Any]:
        """End span and return span data."""
        self._end_time = time.time()
        duration = self._end_time - self._start_time

        span_data = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "service": self.tracer.service_name,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "duration_ms": duration * 1000,
            "attributes": self._attributes,
        }

        trace_id_var.set(self.trace_id)
        return span_data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.end()


def get_tracer(service_name: str = "aicp") -> Tracer:
    """Get tracer instance."""
    return Tracer(service_name)


class HealthCheck:
    """Health check endpoint support."""

    def __init__(self):
        self._checks: dict[str, callable] = {}

    def register(self, name: str, check: callable) -> None:
        """Register a health check."""
        self._checks[name] = check

    async def check(self) -> dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_healthy = True

        for name, check in self._checks.items():
            try:
                if asyncio.iscoroutinefunction(check):
                    await check()
                else:
                    check()
                results[name] = {"status": "healthy"}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
                overall_healthy = False

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "checks": results,
        }

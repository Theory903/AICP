"""API versioning, health checks, and graceful shutdown.

Production-oriented API utilities for:
- version detection + deprecation headers
- liveness/readiness/full health endpoints
- graceful shutdown and lifespan handling
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

HealthState = Literal["healthy", "degraded", "unhealthy"]
CheckResult = dict[str, Any]
MaybeAsyncCheck = Callable[[], Any] | Callable[[], Awaitable[Any]]
ShutdownTask = Callable[[], Any] | Callable[[], Awaitable[Any]]


class APIVersion(Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"


@dataclass(slots=True, frozen=True)
class VersionConfig:
    """Configuration for a single API version."""

    version: APIVersion
    path_prefix: str
    deprecated: bool = False
    sunset_date: str | None = None


class VersionManager:
    """Manage API versions and deprecation metadata."""

    def __init__(
        self,
        *,
        versions: dict[APIVersion, VersionConfig] | None = None,
        default_version: APIVersion = APIVersion.V2,
    ) -> None:
        self._versions: dict[APIVersion, VersionConfig] = versions or {
            APIVersion.V1: VersionConfig(APIVersion.V1, "/api/v1"),
            APIVersion.V2: VersionConfig(APIVersion.V2, "/api/v2"),
        }
        if default_version not in self._versions:
            raise ValueError(f"Default version {default_version.value!r} is not configured")
        self._default_version = default_version

    def get_config(self, version: APIVersion) -> VersionConfig | None:
        """Return version config if present."""
        return self._versions.get(version)

    def get_default(self) -> VersionConfig:
        """Return the default API version config."""
        return self._versions[self._default_version]

    def is_supported(self, version: APIVersion) -> bool:
        """Return whether a version is supported."""
        return version in self._versions

    def resolve_from_path(self, path: str) -> APIVersion:
        """Resolve API version from request path, falling back to default."""
        for version, config in self._versions.items():
            if path.startswith(config.path_prefix):
                return version
        return self._default_version

    def get_deprecation_headers(self, version: APIVersion) -> dict[str, str]:
        """Return deprecation headers for a version when applicable."""
        config = self._versions.get(version)
        successor = self.get_default()

        if config and config.deprecated and config.sunset_date:
            return {
                "Deprecation": f'="{config.sunset_date}"',
                "Sunset": config.sunset_date,
                "Link": f'<{successor.path_prefix}>; rel="successor-version"',
            }

        return {}


def create_version_middleware(app: FastAPI, version_manager: VersionManager) -> None:
    """Attach middleware that resolves API version from request path."""

    @app.middleware("http")
    async def version_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        resolved_version = version_manager.resolve_from_path(request.url.path)
        request.state.api_version = resolved_version

        response = await call_next(request)

        for key, value in version_manager.get_deprecation_headers(resolved_version).items():
            response.headers[key] = value

        return response


@dataclass(slots=True)
class HealthEnvelope:
    """Structured health response."""

    status: HealthState
    checks: dict[str, CheckResult] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class HealthCheckBase(ABC):
    """Base class for health checks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique check name."""
        ...

    @property
    def category(self) -> str:
        """Check category."""
        return "custom"

    @abstractmethod
    async def check(self) -> CheckResult:
        """Run the health check."""
        ...


class LivenessHealthCheck(HealthCheckBase):
    """Liveness probe."""

    @property
    def name(self) -> str:
        return "liveness"

    @property
    def category(self) -> str:
        return "liveness"

    async def check(self) -> CheckResult:
        return {"alive": True, "status": "up"}


class ReadinessHealthCheck(HealthCheckBase):
    """Readiness probe."""

    def __init__(self, ready: bool = True) -> None:
        self._ready = ready

    @property
    def name(self) -> str:
        return "readiness"

    @property
    def category(self) -> str:
        return "readiness"

    @property
    def ready(self) -> bool:
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        self._ready = value

    async def check(self) -> CheckResult:
        return {
            "ready": self._ready,
            "status": "up" if self._ready else "down",
        }


class DependencyHealthCheck(HealthCheckBase):
    """Health check for external dependencies like DB, cache, or queue."""

    def __init__(self, name: str, check_fn: MaybeAsyncCheck) -> None:
        if not name.strip():
            raise ValueError("Dependency health check name cannot be empty")
        self._name = name
        self._check_fn = check_fn

    @property
    def name(self) -> str:
        return f"dependency:{self._name}"

    @property
    def category(self) -> str:
        return "dependency"

    async def check(self) -> CheckResult:
        try:
            result = self._check_fn()
            if asyncio.iscoroutine(result):
                await result
            return {"status": "up"}
        except Exception as exc:
            logger.exception("Dependency health check failed for %s", self._name)
            return {"status": "down", "error": str(exc)}


class HealthCheckRouter:
    """Build FastAPI health endpoints."""

    def __init__(self) -> None:
        self._checks: list[HealthCheckBase] = [
            LivenessHealthCheck(),
            ReadinessHealthCheck(),
        ]

    def add_check(self, check: HealthCheckBase) -> None:
        """Register a health check."""
        self._checks.append(check)

    def list_checks(self) -> list[HealthCheckBase]:
        """Return registered checks."""
        return list(self._checks)

    def _iter_checks(self, *, categories: set[str] | None = None) -> list[HealthCheckBase]:
        """Return checks filtered by category when requested."""
        if categories is None:
            return self.list_checks()
        return [check for check in self._checks if check.category in categories]

    async def _run_checks(self, checks: list[HealthCheckBase]) -> HealthEnvelope:
        """Run checks and compute aggregate health state."""
        results: dict[str, CheckResult] = {}
        has_core_failure = False
        has_dependency_failure = False

        for check in checks:
            result = await check.check()
            results[check.name] = result

            status = result.get("status")
            if check.category in {"liveness", "readiness"}:
                if status == "down" or result.get("alive") is False or result.get("ready") is False:
                    has_core_failure = True
            elif check.category == "dependency" and (status == "down" or "error" in result):
                has_dependency_failure = True

        if has_core_failure:
            overall: HealthState = "unhealthy"
        elif has_dependency_failure:
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthEnvelope(status=overall, checks=results)

    @staticmethod
    def _status_code_for(state: HealthState, *, degraded_ok: bool) -> int:
        """Map health state to HTTP status."""
        if state == "healthy":
            return 200
        if state == "degraded" and degraded_ok:
            return 200
        return 503

    @staticmethod
    def _response(envelope: HealthEnvelope, *, degraded_ok: bool) -> JSONResponse:
        """Convert envelope to JSON response."""
        return JSONResponse(
            content={
                "status": envelope.status,
                "timestamp": envelope.timestamp,
                "checks": envelope.checks,
            },
            status_code=HealthCheckRouter._status_code_for(
                envelope.status,
                degraded_ok=degraded_ok,
            ),
        )

    def create_router(self) -> APIRouter:
        """Create health endpoints router."""
        router = APIRouter()

        @router.get("/health")
        async def health() -> JSONResponse:
            envelope = await self._run_checks(self._iter_checks())
            return self._response(envelope, degraded_ok=True)

        @router.get("/health/live")
        async def liveness() -> JSONResponse:
            envelope = await self._run_checks(self._iter_checks(categories={"liveness"}))
            return self._response(envelope, degraded_ok=False)

        @router.get("/health/ready")
        async def readiness() -> JSONResponse:
            envelope = await self._run_checks(self._iter_checks(categories={"readiness", "dependency"}))
            return self._response(envelope, degraded_ok=False)

        return router


class GracefulShutdown:
    """Graceful shutdown manager for FastAPI applications."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._shutdown_tasks: list[ShutdownTask] = []
        self._is_shutting_down = False
        self._signal_handlers_installed = False

    def register_shutdown_task(self, task: ShutdownTask) -> None:
        """Register a sync or async shutdown task."""
        self._shutdown_tasks.append(task)

    async def shutdown(self) -> None:
        """Run all shutdown tasks exactly once."""
        if self._is_shutting_down:
            return

        self._is_shutting_down = True
        logger.info("Starting graceful shutdown")

        for task in self._shutdown_tasks:
            try:
                result = task()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Shutdown task failed")

        logger.info("Graceful shutdown completed")

    def add_signal_handlers(self) -> None:
        """Register SIGTERM and SIGINT handlers where supported."""
        if self._signal_handlers_installed:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("No running loop available for signal handler registration")
            return

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._schedule_signal_shutdown, sig)
            except NotImplementedError:
                logger.debug("Signal handlers not supported on this platform")
            except RuntimeError:
                logger.debug("Could not install signal handler for %s", sig)

        self._signal_handlers_installed = True

    def _schedule_signal_shutdown(self, sig: signal.Signals) -> None:
        """Schedule graceful shutdown in response to an OS signal."""
        logger.warning("Received signal %s, scheduling graceful shutdown", sig.name)
        asyncio.create_task(self._handle_signal(sig))

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle a shutdown signal."""
        logger.warning("Handling signal %s", sig.name)
        await self.shutdown()


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    """FastAPI lifespan context with graceful shutdown support."""
    shutdown_handler = GracefulShutdown(app)
    shutdown_handler.add_signal_handlers()
    app.state.shutdown_handler = shutdown_handler

    try:
        yield
    finally:
        await shutdown_handler.shutdown()

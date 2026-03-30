"""API versioning, health checks, and graceful shutdown.

Provides production API features.
"""

import asyncio
import signal
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse


class APIVersion(Enum):
    """API version identifiers."""
    V1 = "v1"
    V2 = "v2"


@dataclass
class VersionConfig:
    """API version configuration."""
    version: APIVersion
    path_prefix: str
    deprecated: bool = False
    sunset_date: str | None = None


class VersionManager:
    """Manages API versioning."""
    
    def __init__(self):
        self._versions: dict[APIVersion, VersionConfig] = {
            APIVersion.V1: VersionConfig(APIVersion.V1, "/api/v1"),
            APIVersion.V2: VersionConfig(APIVersion.V2, "/api/v2"),
        }
        self._default_version = APIVersion.V2
        
    def get_config(self, version: APIVersion) -> VersionConfig | None:
        """Get version config."""
        return self._versions.get(version)
        
    def get_default(self) -> VersionConfig:
        """Get default version config."""
        return self._versions[self._default_version]
        
    def is_supported(self, version: APIVersion) -> bool:
        """Check if version is supported."""
        return version in self._versions
        
    def get_deprecation_headers(self, version: APIVersion) -> dict[str, str]:
        """Get deprecation headers for version."""
        config = self._versions.get(version)
        if config and config.deprecated and config.sunset_date:
            return {
                "Deprecation": f'="{config.sunset_date}"',
                "Sunset": config.sunset_date,
                "Link": f'<{self._versions[APIVersion.V2].path_prefix}>; rel="successor-version"',
            }
        return {}


def create_version_middleware(app: FastAPI, version_manager: VersionManager) -> None:
    """Add version detection middleware."""
    
    @app.middleware("http")
    async def version_middleware(request: Request, call_next):
        path = request.url.path
        
        for version in APIVersion:
            config = version_manager.get_config(version)
            if config and path.startswith(config.path_prefix):
                request.state.api_version = version
                break
        else:
            request.state.api_version = version_manager._default_version
            
        response = await call_next(request)
        
        version = getattr(request.state, "api_version", version_manager._default_version)
        deprecation = version_manager.get_deprecation_headers(version)
        for key, value in deprecation.items():
            response.headers[key] = value
            
        return response


@dataclass
class HealthStatus:
    """Health check status."""
    status: str  # healthy, degraded, unhealthy
    checks: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class HealthCheckBase(ABC):
    """Base class for health checks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Health check name."""
        pass
        
    @abstractmethod
    async def check(self) -> dict[str, Any]:
        """Perform health check."""
        pass


class LivenessHealthCheck(HealthCheckBase):
    """Liveness probe - is the service running?"""
    
    @property
    def name(self) -> str:
        return "liveness"
        
    async def check(self) -> dict[str, Any]:
        return {"alive": True}


class ReadinessHealthCheck(HealthCheckBase):
    """Readiness probe - is the service ready to accept traffic?"""
    
    def __init__(self):
        self._ready = True
        
    @property
    def name(self) -> str:
        return "readiness"
        
    @property
    def ready(self) -> bool:
        return self._ready
        
    @ready.setter
    def ready(self, value: bool):
        self._ready = value
        
    async def check(self) -> dict[str, Any]:
        return {"ready": self._ready}


class DependencyHealthCheck(HealthCheckBase):
    """Check external dependencies."""
    
    def __init__(self, name: str, check_fn: Callable):
        self._name = name
        self._check_fn = check_fn
        
    @property
    def name(self) -> str:
        return f"dependency:{self._name}"
        
    async def check(self) -> dict[str, Any]:
        try:
            await self._check_fn()
            return {"status": "up"}
        except Exception as e:
            return {"status": "down", "error": str(e)}


class HealthCheckRouter:
    """Health check router for FastAPI."""
    
    def __init__(self):
        self._checks: list[HealthCheckBase] = [
            LivenessHealthCheck(),
            ReadinessHealthCheck(),
        ]
        
    def add_check(self, check: HealthCheckBase) -> None:
        """Add a health check."""
        self._checks.append(check)
        
    def create_router(self) -> APIRouter:
        """Create health check router."""
        router = APIRouter()
        
        @router.get("/health")
        async def health():
            return await self._full_health()
            
        @router.get("/health/live")
        async def liveness():
            for check in self._checks:
                if check.name == "liveness":
                    result = await check.check()
                    return JSONResponse(
                        result if result.get("alive") else {"alive": False},
                        status_code=200 if result.get("alive") else 503,
                    )
            return {"alive": True}
            
        @router.get("/health/ready")
        async def readiness():
            results = {}
            all_healthy = True
            
            for check in self._checks:
                result = await check.check()
                results[check.name] = result
                if result.get("status") == "down":
                    all_healthy = False
                    
            return JSONResponse(
                results,
                status_code=200 if all_healthy else 503,
            )
            
        return router


class GracefulShutdown:
    """Handles graceful shutdown."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self._shutdown_tasks: list[Callable] = []
        self._is_shutting_down = False
        
    def register_shutdown_task(self, task: Callable) -> None:
        """Register a shutdown task."""
        self._shutdown_tasks.append(task)
        
    async def shutdown(self):
        """Execute graceful shutdown."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        
        for task in self._shutdown_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception:
                pass
                
    def add_signal_handlers(self) -> None:
        """Add signal handlers for shutdown."""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s)),
                )
            except NotImplementedError:
                pass
                
    async def _handle_signal(self, sig):
        """Handle shutdown signal."""
        print(f"Received signal {sig}, starting graceful shutdown...")
        await self.shutdown()


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    shutdown_handler = GracefulShutdown(app)
    shutdown_handler.add_signal_handlers()
    
    yield
    
    await shutdown_handler.shutdown()

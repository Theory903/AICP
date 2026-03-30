"""Multi-tenancy support for AICP.

Provides tenant isolation, quotas, and per-tenant configuration.
"""

import secrets
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tenant:
    """Represents a tenant in the platform."""
    id: str
    name: str
    created_at: float = field(default_factory=time.time)
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class TenantQuota:
    """Quota limits for a tenant."""
    tenant_id: str
    max_api_calls_per_minute: int = 60
    max_concurrent_requests: int = 10
    max_storage_mb: int = 100
    max_workflows: int = 100
    max_approvals_per_day: int = 1000


class TenantContext:
    """Context for current tenant request."""

    _current: "TenantContext | None" = None

    def __init__(self, tenant_id: str, metadata: dict[str, Any] | None = None):
        self.tenant_id = tenant_id
        self.metadata = metadata or {}
        self._start_time = time.time()

    @classmethod
    def get_current(cls) -> "TenantContext | None":
        """Get current tenant context."""
        return cls._current

    @classmethod
    def set_current(cls, context: "TenantContext | None") -> None:
        """Set current tenant context."""
        cls._current = context

    @classmethod
    def clear_current(cls) -> None:
        """Clear current tenant context."""
        cls._current = None

    def __enter__(self):
        TenantContext._current = self
        return self

    def __exit__(self, *args):
        TenantContext._current = None


class TenantManager:
    """Manages tenants and tenant isolation."""

    def __init__(self):
        self._tenants: dict[str, Tenant] = {}
        self._quotas: dict[str, TenantQuota] = {}
        self._api_keys: dict[str, tuple[str, str]] = {}  # key -> (tenant_id, key_id)

    def create_tenant(
        self,
        name: str,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = secrets.token_hex(12)
        tenant = Tenant(
            id=tenant_id,
            name=name,
            config=config or {},
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        self._quotas[tenant_id] = TenantQuota(tenant_id=tenant_id)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def create_api_key(self, tenant_id: str, name: str = "default") -> tuple[str, str]:
        """Create API key for tenant.

        Returns:
            Tuple of (api_key, key_id)
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        key_id = secrets.token_hex(8)
        api_key = f"aicp_{tenant_id[:8]}_{secrets.token_hex(24)}"
        self._api_keys[api_key] = (tenant_id, key_id)
        return api_key, key_id

    def verify_api_key(self, api_key: str) -> str | None:
        """Verify API key and return tenant ID."""
        result = self._api_keys.get(api_key)
        if result:
            tenant_id, _ = result
            tenant = self._tenants.get(tenant_id)
            if tenant and tenant.is_active:
                return tenant_id
        return None

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            return True
        return False

    def get_quota(self, tenant_id: str) -> TenantQuota | None:
        """Get quota for tenant."""
        return self._quotas.get(tenant_id)

    def update_quota(self, tenant_id: str, quota: TenantQuota) -> None:
        """Update quota for tenant."""
        self._quotas[tenant_id] = quota

    def list_tenants(self) -> list[Tenant]:
        """List all tenants."""
        return list(self._tenants.values())

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.is_active = False
            return True
        return False


class TenantIsolation:
    """Provides data isolation per tenant."""

    def __init__(self, tenant_manager: TenantManager):
        self._manager = tenant_manager

    def get_tenant_store(self, tenant_id: str) -> dict[str, Any]:
        """Get tenant-isolated storage.

        Each tenant gets isolated storage keys.
        """
        return {"tenant_id": tenant_id, "_prefix": f"tenant:{tenant_id}"}

    def filter_tenant_data(
        self,
        data: list[dict[str, Any]],
        tenant_id: str,
        tenant_field: str = "tenant_id",
    ) -> list[dict[str, Any]]:
        """Filter data to only include tenant's data."""
        return [item for item in data if item.get(tenant_field) == tenant_id]

    def isolation_middleware(self, request: dict[str, Any]) -> dict[str, Any]:
        """Add tenant isolation to request context."""
        api_key = request.get("headers", {}).get("X-API-Key") or request.get("api_key")

        if api_key:
            tenant_id = self._manager.verify_api_key(api_key)
            if tenant_id:
                request["tenant_id"] = tenant_id

        return request

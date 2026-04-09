"""Multi-tenancy support for AICP.

Provides tenant isolation, quotas, API key verification,
and per-tenant request context.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_current_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "aicp_current_tenant_context",
    default=None,
)


@dataclass(slots=True)
class Tenant:
    """Represents a tenant in the platform."""

    id: str
    name: str
    created_at: float = field(default_factory=time.time)
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass(slots=True)
class TenantQuota:
    """Quota limits for a tenant."""

    tenant_id: str
    max_api_calls_per_minute: int = 60
    max_concurrent_requests: int = 10
    max_storage_mb: int = 100
    max_workflows: int = 100
    max_approvals_per_day: int = 1000


@dataclass(slots=True)
class TenantApiKeyRecord:
    """Stored metadata for a tenant API key."""

    tenant_id: str
    key_id: str
    key_name: str
    key_hash: str
    created_at: float = field(default_factory=time.time)
    last_used_at: float | None = None
    expires_at: float | None = None
    is_active: bool = True

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < time.time()


class TenantContext:
    """Context for the current tenant request."""

    def __init__(self, tenant_id: str, metadata: dict[str, Any] | None = None):
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        self.tenant_id = tenant_id
        self.metadata = metadata or {}
        self._start_time = time.time()
        self._token = None

    @property
    def started_at(self) -> float:
        """Return the context start time."""
        return self._start_time

    @classmethod
    def get_current(cls) -> TenantContext | None:
        """Get current tenant context."""
        return _current_tenant_context.get()

    @classmethod
    def set_current(cls, context: TenantContext | None) -> None:
        """Set current tenant context."""
        _current_tenant_context.set(context)

    @classmethod
    def clear_current(cls) -> None:
        """Clear current tenant context."""
        _current_tenant_context.set(None)

    def __enter__(self) -> TenantContext:
        self._token = _current_tenant_context.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            _current_tenant_context.reset(self._token)
            self._token = None
        else:
            _current_tenant_context.set(None)


class TenantManager:
    """Manages tenants, quotas, and tenant API keys."""

    def __init__(self):
        self._tenants: dict[str, Tenant] = {}
        self._quotas: dict[str, TenantQuota] = {}
        self._api_keys_by_id: dict[str, TenantApiKeyRecord] = {}
        self._api_key_lookup: dict[str, str] = {}  # key_hash -> key_id

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """Hash an API key for secure lookup."""
        if not api_key:
            raise ValueError("api_key cannot be empty")
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def create_tenant(
        self,
        name: str,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        """Create a new tenant."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("tenant name cannot be empty")

        tenant_id = secrets.token_hex(12)
        tenant = Tenant(
            id=tenant_id,
            name=cleaned_name,
            config=config or {},
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        self._quotas[tenant_id] = TenantQuota(tenant_id=tenant_id)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def require_tenant(self, tenant_id: str) -> Tenant:
        """Get tenant by ID or raise."""
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant not found: {tenant_id}")
        return tenant

    def create_api_key(
        self,
        tenant_id: str,
        name: str = "default",
        expires_in_seconds: float | None = None,
    ) -> tuple[str, str]:
        """Create API key for tenant.

        Returns:
            Tuple of (api_key, key_id)
        """
        tenant = self.require_tenant(tenant_id)
        if not tenant.is_active:
            raise ValueError(f"Tenant is inactive: {tenant_id}")

        if expires_in_seconds is not None and expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be > 0 when provided")

        key_id = secrets.token_hex(8)
        api_key = f"aicp_{tenant_id[:8]}_{secrets.token_hex(24)}"
        key_hash = self._hash_api_key(api_key)

        record = TenantApiKeyRecord(
            tenant_id=tenant_id,
            key_id=key_id,
            key_name=name.strip() or "default",
            key_hash=key_hash,
            expires_at=(time.time() + expires_in_seconds) if expires_in_seconds else None,
        )

        self._api_keys_by_id[key_id] = record
        self._api_key_lookup[key_hash] = key_id
        return api_key, key_id

    def verify_api_key(self, api_key: str) -> str | None:
        """Verify API key and return tenant ID."""
        try:
            key_hash = self._hash_api_key(api_key)
        except ValueError:
            return None

        key_id = self._api_key_lookup.get(key_hash)
        if key_id is None:
            return None

        record = self._api_keys_by_id.get(key_id)
        if record is None or not record.is_active or record.is_expired:
            return None

        tenant = self._tenants.get(record.tenant_id)
        if tenant is None or not tenant.is_active:
            return None

        record.last_used_at = time.time()
        return record.tenant_id

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key by raw key value."""
        try:
            key_hash = self._hash_api_key(api_key)
        except ValueError:
            return False

        key_id = self._api_key_lookup.get(key_hash)
        if key_id is None:
            return False

        record = self._api_keys_by_id.get(key_id)
        if record is None:
            return False

        record.is_active = False
        return True

    def revoke_api_key_by_id(self, key_id: str) -> bool:
        """Revoke an API key by key ID."""
        record = self._api_keys_by_id.get(key_id)
        if record is None:
            return False

        record.is_active = False
        return True

    def list_api_keys(self, tenant_id: str) -> list[dict[str, Any]]:
        """List API key metadata for a tenant."""
        self.require_tenant(tenant_id)
        return [
            {
                "key_id": record.key_id,
                "key_name": record.key_name,
                "created_at": record.created_at,
                "last_used_at": record.last_used_at,
                "expires_at": record.expires_at,
                "is_active": record.is_active,
                "is_expired": record.is_expired,
            }
            for record in self._api_keys_by_id.values()
            if record.tenant_id == tenant_id
        ]

    def get_quota(self, tenant_id: str) -> TenantQuota | None:
        """Get quota for tenant."""
        return self._quotas.get(tenant_id)

    def require_quota(self, tenant_id: str) -> TenantQuota:
        """Get quota for tenant or raise."""
        quota = self.get_quota(tenant_id)
        if quota is None:
            raise ValueError(f"Quota not found for tenant: {tenant_id}")
        return quota

    def update_quota(self, tenant_id: str, quota: TenantQuota) -> None:
        """Update quota for tenant."""
        if quota.tenant_id != tenant_id:
            raise ValueError("quota.tenant_id must match tenant_id")
        self.require_tenant(tenant_id)
        self._quotas[tenant_id] = quota

    def list_tenants(self, active_only: bool = False) -> list[Tenant]:
        """List all tenants."""
        tenants = list(self._tenants.values())
        if active_only:
            tenants = [tenant for tenant in tenants if tenant.is_active]
        return tenants

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant."""
        tenant = self._tents_get(tenant_id)
        if tenant is None:
            return False

        tenant.is_active = False

        # Revoke all active API keys for the tenant
        for record in self._api_keys_by_id.values():
            if record.tenant_id == tenant_id:
                record.is_active = False

        return True

    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False

        tenant.is_active = True
        return True

    def _tents_get(self, tenant_id: str) -> Tenant | None:
        """Internal helper for tenant fetch."""
        return self._tenants.get(tenant_id)


class TenantIsolation:
    """Provides tenant isolation helpers."""

    def __init__(self, tenant_manager: TenantManager):
        self._manager = tenant_manager

    def get_tenant_store(self, tenant_id: str) -> dict[str, Any]:
        """Get tenant-isolated storage information."""
        self._manager.require_tenant(tenant_id)
        return {
            "tenant_id": tenant_id,
            "storage_prefix": f"tenant:{tenant_id}",
        }

    def storage_key(self, tenant_id: str, key: str) -> str:
        """Build a tenant-isolated storage key."""
        self._manager.require_tenant(tenant_id)
        cleaned_key = key.strip()
        if not cleaned_key:
            raise ValueError("key cannot be empty")
        return f"tenant:{tenant_id}:{cleaned_key}"

    def filter_tenant_data(
        self,
        data: list[dict[str, Any]],
        tenant_id: str,
        tenant_field: str = "tenant_id",
    ) -> list[dict[str, Any]]:
        """Filter data to only include a tenant's data."""
        self._manager.require_tenant(tenant_id)
        return [item for item in data if item.get(tenant_field) == tenant_id]

    def assert_tenant_access(
        self,
        item: dict[str, Any],
        tenant_id: str,
        tenant_field: str = "tenant_id",
    ) -> None:
        """Assert that an item belongs to a tenant."""
        item_tenant_id = item.get(tenant_field)
        if item_tenant_id != tenant_id:
            raise PermissionError(f"Tenant '{tenant_id}' cannot access data for tenant '{item_tenant_id}'")

    def isolation_middleware(self, request: dict[str, Any]) -> dict[str, Any]:
        """Add tenant isolation to request context.

        Supports:
        - request["headers"]["X-API-Key"]
        - request["api_key"]
        """
        headers = request.get("headers", {}) or {}
        api_key = headers.get("X-API-Key") or headers.get("x-api-key") or request.get("api_key")

        if api_key:
            tenant_id = self._manager.verify_api_key(api_key)
            if tenant_id:
                request["tenant_id"] = tenant_id

        return request

"""Secret management and cloud storage for AICP.

Provides integration with external secret stores and cloud storage.
"""

from __future__ import annotations

import asyncio
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class SecretStoreError(Exception):
    """Base error for secret storage operations."""


class SecretStore(ABC):
    """Abstract secret store interface."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get secret value."""
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Set secret value."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete secret."""
        raise NotImplementedError

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List secret keys."""
        raise NotImplementedError


class EnvSecretStore(SecretStore):
    """Secret store backed by environment variables.

    Useful for local development and simple deployments.
    """

    def __init__(self, prefix: str = "AICP_SECRET_"):
        cleaned_prefix = prefix.strip()
        if not cleaned_prefix:
            raise ValueError("prefix cannot be empty")
        self.prefix = cleaned_prefix

    def _full_key(self, key: str) -> str:
        cleaned = key.strip()
        if not cleaned:
            raise ValueError("secret key cannot be empty")
        return f"{self.prefix}{cleaned}"

    async def get(self, key: str) -> str | None:
        return os.environ.get(self._full_key(key))

    async def set(self, key: str, value: str) -> None:
        os.environ[self._full_key(key)] = value

    async def delete(self, key: str) -> bool:
        full_key = self._full_key(key)
        if full_key in os.environ:
            del os.environ[full_key]
            return True
        return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        full_prefix = self._full_key(prefix) if prefix else self.prefix
        keys = [env_key[len(self.prefix) :] for env_key in os.environ if env_key.startswith(full_prefix)]
        return sorted(keys)


class HashiCorpVaultStore(SecretStore):
    """Secret store backed by HashiCorp Vault."""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        mount_point: str = "secret",
        namespace: str | None = None,
    ):
        self.url = url or os.environ.get("VAULT_ADDR")
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.mount_point = mount_point
        self.namespace = namespace
        self._client: Any | None = None

        if not self.url:
            raise ValueError("Vault URL is required")
        if not self.token:
            raise ValueError("Vault token is required")

    def _get_client(self) -> Any:
        """Get or create Vault client."""
        if self._client is None:
            try:
                import hvac
            except ImportError as exc:
                raise RuntimeError("hvac package required for Vault integration") from exc

            self._client = hvac.Client(
                url=self.url,
                token=self.token,
                namespace=self.namespace,
            )
        return self._client

    async def _run_blocking(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def get(self, key: str) -> str | None:
        client = self._get_client()
        try:
            result = await self._run_blocking(
                client.secrets.kv.v2.read_secret_version,
                path=key,
                mount_point=self.mount_point,
            )
            return result["data"]["data"].get("value")
        except Exception:
            return None

    async def set(self, key: str, value: str) -> None:
        client = self._get_client()
        await self._run_blocking(
            client.secrets.kv.v2.create_or_update_secret,
            path=key,
            secret={"value": value},
            mount_point=self.mount_point,
        )

    async def delete(self, key: str) -> bool:
        client = self._get_client()
        try:
            await self._run_blocking(
                client.secrets.kv.v2.delete_metadata_and_all_versions,
                path=key,
                mount_point=self.mount_point,
            )
            return True
        except Exception:
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        client = self._get_client()
        try:
            result = await self._run_blocking(
                client.secrets.kv.v2.list_secrets,
                path=prefix,
                mount_point=self.mount_point,
            )
            return sorted(result["data"]["keys"])
        except Exception:
            return []


class AWSSecretsManagerStore(SecretStore):
    """Secret store backed by AWS Secrets Manager."""

    def __init__(self, region_name: str | None = None):
        self.region_name = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError("boto3 required for AWS integration") from exc

            self._client = boto3.client(
                "secretsmanager",
                region_name=self.region_name,
            )
        return self._client

    async def _run_blocking(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def get(self, key: str) -> str | None:
        client = self._get_client()
        try:
            result = await self._run_blocking(
                client.get_secret_value,
                SecretId=key,
            )
            return result.get("SecretString")
        except Exception:
            return None

    async def set(self, key: str, value: str) -> None:
        client = self._get_client()
        try:
            await self._run_blocking(
                client.put_secret_value,
                SecretId=key,
                SecretString=value,
            )
        except Exception:
            # Fallback for first write when secret does not exist yet
            await self._run_blocking(
                client.create_secret,
                Name=key,
                SecretString=value,
            )

    async def delete(self, key: str) -> bool:
        client = self._get_client()
        try:
            await self._run_blocking(
                client.delete_secret,
                SecretId=key,
                ForceDeleteWithoutRecovery=True,
            )
            return True
        except Exception:
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        client = self._get_client()
        try:
            kwargs: dict[str, Any] = {}
            if prefix:
                kwargs["Filters"] = [{"Key": "name", "Values": [prefix]}]

            result = await self._run_blocking(client.list_secrets, **kwargs)
            return sorted(secret["Name"] for secret in result.get("SecretList", []))
        except Exception:
            return []


class SecretManager:
    """Central secret management with caching."""

    def __init__(self, store: SecretStore, cache_ttl: int = 300):
        if cache_ttl < 0:
            raise ValueError("cache_ttl must be >= 0")

        self._store = store
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = cache_ttl

    async def get(self, key: str) -> str | None:
        now = time.time()

        if key in self._cache:
            value, cached_at = self._cache[key]
            if self._cache_ttl == 0 or now - cached_at < self._cache_ttl:
                return value

        value = await self._store.get(key)
        if value is not None:
            self._cache[key] = (value, now)
        else:
            self._cache.pop(key, None)
        return value

    async def set(self, key: str, value: str) -> None:
        await self._store.set(key, value)
        self._cache[key] = (value, time.time())

    async def delete(self, key: str) -> bool:
        result = await self._store.delete(key)
        self._cache.pop(key, None)
        return result

    async def list_keys(self, prefix: str = "") -> list[str]:
        return await self._store.list_keys(prefix=prefix)

    def clear_cache(self) -> None:
        self._cache.clear()


class CloudAuditStorage:
    """Cloud storage for audit logs."""

    def __init__(self):
        self._storage = None

    async def upload_audit_log(
        self,
        content: str,
        filename: str,
        bucket: str | None = None,
    ) -> str | None:
        """Upload audit log to cloud storage."""
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            return await self._upload_s3(content, filename, bucket)

        if os.environ.get("GCS_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return await self._upload_gcs(content, filename, bucket)

        return None

    async def _upload_s3(
        self,
        content: str,
        filename: str,
        bucket: str | None = None,
    ) -> str | None:
        try:
            import boto3
        except ImportError:
            return None

        target_bucket = bucket or os.environ.get("AWS_AUDIT_BUCKET", "aicp-audit-logs")
        key = f"audit/{filename}"
        client = boto3.client("s3")

        await asyncio.to_thread(
            client.put_object,
            Bucket=target_bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
        )

        return f"s3://{target_bucket}/{key}"

    async def _upload_gcs(
        self,
        content: str,
        filename: str,
        bucket: str | None = None,
    ) -> str | None:
        try:
            from google.cloud import storage
        except ImportError:
            return None

        target_bucket = bucket or os.environ.get("GCS_AUDIT_BUCKET", "aicp-audit-logs")
        key = f"audit/{filename}"

        client = storage.Client()
        blob = client.bucket(target_bucket).blob(key)

        await asyncio.to_thread(
            blob.upload_from_string,
            content,
            content_type="application/json",
        )

        return f"gs://{target_bucket}/{key}"

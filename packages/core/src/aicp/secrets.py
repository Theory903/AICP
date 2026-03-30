"""Secret management and cloud storage for AICP.

Provides integration with external secret stores and cloud storage.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any


class SecretStore(ABC):
    """Abstract secret store interface."""
    
    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get secret value."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Set secret value."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete secret."""
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List secret keys."""
        pass


class EnvSecretStore(SecretStore):
    """Secret store backed by environment variables."""
    
    def __init__(self, prefix: str = "AICP_SECRET_"):
        self.prefix = prefix
        
    async def get(self, key: str) -> str | None:
        return os.environ.get(f"{self.prefix}{key}")
    
    async def set(self, key: str, value: str) -> None:
        os.environ[f"{self.prefix}{key}"] = value
        
    async def delete(self, key: str) -> bool:
        full_key = f"{self.prefix}{key}"
        if full_key in os.environ:
            del os.environ[full_key]
            return True
        return False
        
    async def list_keys(self, prefix: str = "") -> list[str]:
        return [
            k[len(self.prefix):]
            for k in os.environ
            if k.startswith(self.prefix) and (not prefix or k.startswith(f"{self.prefix}{prefix}"))
        ]


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
        self._client = None
        
    def _get_client(self):
        """Get or create Vault client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.url,
                    token=self.token,
                    namespace=self.namespace,
                )
            except ImportError:
                raise RuntimeError("hvac package required for Vault integration")
        return self._client
        
    async def get(self, key: str) -> str | None:
        client = self._get_client()
        try:
            result = client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point,
            )
            return result["data"]["data"].get("value")
        except Exception:
            return None
    
    async def set(self, key: str, value: str) -> None:
        client = self._get_client()
        client.secrets.kv.v2.create_or_update_secret(
            path=key,
            secret={"value": value},
            mount_point=self.mount_point,
        )
        
    async def delete(self, key: str) -> bool:
        client = self._get_client()
        try:
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key,
                mount_point=self.mount_point,
            )
            return True
        except Exception:
            return False
            
    async def list_keys(self, prefix: str = "") -> list[str]:
        client = self._get_client()
        try:
            result = client.secrets.kv.v2.list_secrets(
                path=prefix,
                mount_point=self.mount_point,
            )
            return result["data"]["keys"]
        except Exception:
            return []


class AWSSecretsManagerStore(SecretStore):
    """Secret store backed by AWS Secrets Manager."""
    
    def __init__(self, region_name: str | None = None):
        self.region_name = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client = None
        
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("secretsmanager", region_name=self.region_name)
            except ImportError:
                raise RuntimeError("boto3 required for AWS integration")
        return self._client
        
    async def get(self, key: str) -> str | None:
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                client.get_secret_value,
                {"SecretId": key},
            )
            return result.get("SecretString")
        except Exception:
            return None
    
    async def set(self, key: str, value: str) -> None:
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            client.put_secret_value,
            {"SecretId": key, "SecretString": value},
        )
        
    async def delete(self, key: str) -> bool:
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                client.delete_secret,
                {"SecretId": key, "ForceDeleteWithoutRecovery": True},
            )
            return True
        except Exception:
            return False
            
    async def list_keys(self, prefix: str = "") -> list[str]:
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                client.list_secrets,
                {"Filters": [{"Key": "name", "Values": [prefix]}]} if prefix else {},
            )
            return [s["Name"] for s in result.get("SecretList", [])]
        except Exception:
            return []


class SecretManager:
    """Central secret management with caching."""
    
    def __init__(self, store: SecretStore, cache_ttl: int = 300):
        self._store = store
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = cache_ttl
        
    async def get(self, key: str) -> str | None:
        import time
        now = time.time()
        
        if key in self._cache:
            value, cached_at = self._cache[key]
            if now - cached_at < self._cache_ttl:
                return value
                
        value = await self._store.get(key)
        if value:
            self._cache[key] = (value, now)
        return value
        
    async def set(self, key: str, value: str) -> None:
        await self._store.set(key, value)
        self._cache[key] = (value, time.time())
        
    async def delete(self, key: str) -> bool:
        result = await self._store.delete(key)
        if key in self._cache:
            del self._cache[key]
        return result
        
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
        # Try S3 first
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            return await self._upload_s3(content, filename, bucket)
        # Try GCS
        if os.environ.get("GCS_CREDENTIALS"):
            return await self._upload_gcs(content, filename, bucket)
        return None
        
    async def _upload_s3(
        self,
        content: str,
        filename: str,
        bucket: str | None = None,
    ) -> str | None:
        import asyncio
        try:
            import boto3
        except ImportError:
            return None
            
        bucket = bucket or os.environ.get("AWS_AUDIT_BUCKET", "aicp-audit-logs")
        
        client = boto3.client("s3")
        loop = asyncio.get_event_loop()
        
        key = f"audit/{filename}"
        
        await loop.run_in_executor(
            None,
            client.put_object,
            {"Bucket": bucket, "Key": key, "Body": content},
        )
        
        return f"s3://{bucket}/{key}"
        
    async def _upload_gcs(
        self,
        content: str,
        filename: str,
        bucket: str | None = None,
    ) -> str | None:
        import asyncio
        try:
            from google.cloud import storage
        except ImportError:
            return None
            
        bucket = bucket or os.environ.get("GCS_AUDIT_BUCKET", "aicp-audit-logs")
        
        client = storage.Client()
        blob = client.bucket(bucket).blob(f"audit/{filename}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, blob.upload_from_string, content)
        
        return f"gs://{bucket}/audit/{filename}"

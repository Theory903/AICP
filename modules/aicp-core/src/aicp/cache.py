"""Redis caching for AICP.

Provides distributed caching, cache decorators, and Redis-backed rate limiting.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

import redis.asyncio as redis
from redis.exceptions import RedisError

P = ParamSpec("P")
T = TypeVar("T")


class CacheError(Exception):
    """Base exception for cache-related failures."""


class RedisCache:
    """Redis-backed cache."""

    def __init__(
        self,
        url: str | None = None,
        host: str | None = None,
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        prefix: str = "aicp:",
        default_ttl: int = 300,
    ) -> None:
        if default_ttl <= 0:
            raise ValueError("default_ttl must be > 0")
        if not prefix:
            raise ValueError("prefix cannot be empty")

        if url:
            self._url = url
        else:
            host = host or os.environ.get("REDIS_HOST", "localhost")
            password = password or os.environ.get("REDIS_PASSWORD")
            if password:
                self._url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                self._url = f"redis://{host}:{port}/{db}"

        self.prefix = prefix
        self.default_ttl = default_ttl
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._url, decode_responses=True)
        return self._client

    def _full_key(self, key: str) -> str:
        if not key:
            raise ValueError("key cannot be empty")
        return f"{self.prefix}{key}"

    @staticmethod
    def _encode_value(value: Any) -> str:
        """Serialize value for Redis storage.

        Always stores JSON so round-trips are predictable.
        """
        try:
            return json.dumps(value, default=str, separators=(",", ":"))
        except TypeError as exc:
            raise CacheError(f"Value is not JSON serializable: {exc}") from exc

    @staticmethod
    def _decode_value(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Keep backward compatibility if old raw string values already exist.
            return value

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            value = await client.get(full_key)
        except RedisError as exc:
            raise CacheError(f"Redis get failed for key '{key}': {exc}") from exc

        if value is None:
            return None
        return self._decode_value(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache."""
        client = await self._get_client()
        full_key = self._full_key(key)
        encoded_value = self._encode_value(value)
        ttl_to_use = self.default_ttl if ttl is None else ttl
        if ttl_to_use <= 0:
            raise ValueError("ttl must be > 0")

        try:
            await client.set(full_key, encoded_value, ex=ttl_to_use)
        except RedisError as exc:
            raise CacheError(f"Redis set failed for key '{key}': {exc}") from exc

    async def set_if_absent(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a key only if it does not already exist."""
        client = await self._get_client()
        full_key = self._full_key(key)
        encoded_value = self._encode_value(value)
        ttl_to_use = self.default_ttl if ttl is None else ttl
        if ttl_to_use <= 0:
            raise ValueError("ttl must be > 0")

        try:
            result = await client.set(full_key, encoded_value, ex=ttl_to_use, nx=True)
        except RedisError as exc:
            raise CacheError(f"Redis set_if_absent failed for key '{key}': {exc}") from exc

        return bool(result)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            result = await client.delete(full_key)
        except RedisError as exc:
            raise CacheError(f"Redis delete failed for key '{key}': {exc}") from exc
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            result = await client.exists(full_key)
        except RedisError as exc:
            raise CacheError(f"Redis exists failed for key '{key}': {exc}") from exc
        return result > 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment integer counter."""
        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            return await client.incrby(full_key, amount)
        except RedisError as exc:
            raise CacheError(f"Redis increment failed for key '{key}': {exc}") from exc

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        if ttl <= 0:
            raise ValueError("ttl must be > 0")

        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            return bool(await client.expire(full_key, ttl))
        except RedisError as exc:
            raise CacheError(f"Redis expire failed for key '{key}': {exc}") from exc

    async def ttl(self, key: str) -> int | None:
        """Get remaining TTL in seconds.

        Returns None if the key does not exist or has no expiry.
        """
        client = await self._get_client()
        full_key = self._full_key(key)
        try:
            value = await client.ttl(full_key)
        except RedisError as exc:
            raise CacheError(f"Redis ttl failed for key '{key}': {exc}") from exc

        if value in (-1, -2):
            return None
        return int(value)

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern.

        Intended for debugging/admin paths, not hot production loops.
        """
        client = await self._get_client()
        full_pattern = self._full_key(pattern)
        try:
            keys = await client.keys(full_pattern)
        except RedisError as exc:
            raise CacheError(f"Redis keys failed for pattern '{pattern}': {exc}") from exc

        return [k[len(self.prefix) :] for k in keys]

    async def clear(self) -> int:
        """Clear all keys with the configured prefix.

        Returns number of deleted keys.
        """
        client = await self._get_client()
        try:
            keys = await client.keys(f"{self.prefix}*")
            if not keys:
                return 0
            return int(await client.delete(*keys))
        except RedisError as exc:
            raise CacheError(f"Redis clear failed for prefix '{self.prefix}': {exc}") from exc

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        client = await self._get_client()
        try:
            result = await client.ping()
        except RedisError as exc:
            raise CacheError(f"Redis ping failed: {exc}") from exc
        return bool(result)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class CacheDecorator:
    """Decorator helper for caching async function results."""

    def __init__(self, cache: RedisCache, key_prefix: str = "") -> None:
        self.cache = cache
        self.key_prefix = key_prefix

    @staticmethod
    def _default_key(func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        payload = {
            "args": args,
            "kwargs": kwargs,
        }
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{func_name}:{digest}"

    def cached(
        self,
        ttl: int | None = None,
        key_func: Callable[P, str] | None = None,
        cache_none: bool = True,
    ) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
        """Decorator to cache async function results.

        Args:
            ttl: TTL override in seconds
            key_func: Optional custom key generator
            cache_none: Whether None results should be cached
        """

        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                cache_key = (
                    key_func(*args, **kwargs)
                    if key_func is not None
                    else self._default_key(func.__name__, args, kwargs)
                )
                cache_key = f"{self.key_prefix}{cache_key}"

                cached_value = await self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = await func(*args, **kwargs)

                if result is not None or cache_none:
                    await self.cache.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


class RateLimiterRedis:
    """Redis-backed fixed-window rate limiter for distributed systems."""

    def __init__(self, cache: RedisCache, key: str, limit: int, window: int) -> None:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        if window <= 0:
            raise ValueError("window must be > 0")

        self.cache = cache
        self.key = f"ratelimit:{key}"
        self.limit = limit
        self.window = window

    def _window_key(self, now: int | None = None) -> tuple[str, int]:
        current = int(time.time()) if now is None else now
        bucket = current // self.window
        return f"{self.key}:{bucket}", current

    async def check(self) -> bool:
        """Check whether a request is allowed."""
        window_key, _ = self._window_key()

        count = await self.cache.increment(window_key, 1)
        if count == 1:
            await self.cache.expire(window_key, self.window)

        return count <= self.limit

    async def get_current_count(self) -> int:
        """Get the current request count for the active window."""
        window_key, _ = self._window_key()
        value = await self.cache.get(window_key)
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise CacheError(f"Rate limiter counter for '{window_key}' is not numeric") from None

    async def get_remaining(self) -> int:
        """Get remaining allowed requests in the current window."""
        count = await self.get_current_count()
        return max(0, self.limit - count)

    async def get_retry_after(self) -> int:
        """Get seconds until the current window resets."""
        window_key, now = self._window_key()
        ttl = await self.cache.ttl(window_key)
        if ttl is not None:
            return max(0, ttl)

        # Fallback when the key is absent or no TTL is set.
        elapsed_in_window = now % self.window
        return max(0, self.window - elapsed_in_window)

    async def get_headers(self) -> dict[str, str]:
        """Return standard-ish rate-limit response headers."""
        remaining = await self.get_remaining()
        retry_after = await self.get_retry_after()
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "Retry-After": str(retry_after),
        }

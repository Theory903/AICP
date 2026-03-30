"""Redis caching for AICP.

Provides distributed caching with Redis.
"""

import json
import os
from typing import Any

import redis.asyncio as redis


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
    ):
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

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"
        value = await client.get(full_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        ttl = ttl or self.default_ttl
        await client.set(full_key, value, ex=ttl)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"
        result = await client.delete(full_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"
        return await client.exists(full_key) > 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"
        return await client.incrby(full_key, amount)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        client = await self._get_client()
        full_key = f"{self.prefix}{key}"
        return await client.expire(full_key, ttl)

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        client = await self._get_client()
        full_pattern = f"{self.prefix}{pattern}"
        return [k[len(self.prefix):] for k in await client.keys(full_pattern)]

    async def clear(self) -> None:
        """Clear all keys with prefix."""
        client = await self._get_client()
        keys = await client.keys(f"{self.prefix}*")
        if keys:
            await client.delete(*keys)

    async def close(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.close()
            self._client = None


class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(self, cache: RedisCache, key_prefix: str = ""):
        self.cache = cache
        self.key_prefix = key_prefix

    def cached(self, ttl: int | None = None, key_func=None):
        """Decorator to cache function results."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{self.key_prefix}{func.__name__}:{str(args)}:{str(kwargs)}"

                cached_value = await self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result

                await self.cache.set(cache_key, result, ttl)
                return result

            return wrapper
        return decorator


class RateLimiterRedis:
    """Redis-backed rate limiter for distributed systems."""

    def __init__(self, cache: RedisCache, key: str, limit: int, window: int):
        self.cache = cache
        self.key = f"ratelimit:{key}"
        self.limit = limit
        self.window = window

    async def check(self) -> bool:
        """Check if request is allowed."""
        import time
        now = int(time.time())
        window_key = f"{self.key}:{now // self.window}"

        count = await self.cache.cache.increment(window_key, 1)
        if count == 1:
            await self.cache.cache.expire(window_key, self.window)

        return count <= self.limit

    async def get_remaining(self) -> int:
        """Get remaining requests."""
        import time
        now = int(time.time())
        window_key = f"{self.key}:{now // self.window}"

        value = await self.cache.get(window_key)
        if value is None:
            return self.limit

        return max(0, self.limit - value)

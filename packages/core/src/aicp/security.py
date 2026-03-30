"""Security utilities for AICP.

Provides rate limiting, API key rotation, and audit signing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded: {limit} requests per {window_seconds}s")


class RateLimiter:
    """Sliding-window rate limiter.

    Tracks request timestamps per key within a fixed window.
    """

    def __init__(self, requests_per_window: int, window_seconds: float):
        if requests_per_window < 1:
            raise ValueError("requests_per_window must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _prune_bucket(self, key: str, now: float) -> list[float]:
        """Remove expired timestamps for a key."""
        window_start = now - self.window_seconds
        bucket = self._buckets[key]
        bucket[:] = [timestamp for timestamp in bucket if timestamp > window_start]
        return bucket

    def check(self, key: str, cost: int = 1) -> None:
        """Check if request is allowed.

        Args:
            key: Rate limit key such as user_id or api_key.
            cost: Cost of this request.

        Raises:
            RateLimitError: If limit is exceeded.
        """
        if not key:
            raise ValueError("key cannot be empty")
        if cost < 1:
            raise ValueError("cost must be >= 1")

        now = time.monotonic()
        bucket = self._prune_bucket(key, now)

        if len(bucket) + cost > self.requests_per_window:
            raise RateLimitError(self.requests_per_window, self.window_seconds)

        bucket.extend([now] * cost)

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key."""
        if not key:
            raise ValueError("key cannot be empty")

        now = time.monotonic()
        bucket = self._prune_bucket(key, now)
        return max(0, self.requests_per_window - len(bucket))

    def get_reset_after(self, key: str) -> float:
        """Get seconds until the oldest request leaves the window."""
        if not key:
            raise ValueError("key cannot be empty")

        now = time.monotonic()
        bucket = self._prune_bucket(key, now)
        if not bucket:
            return 0.0
        oldest = min(bucket)
        return max(0.0, self.window_seconds - (now - oldest))

    def reset(self, key: str) -> None:
        """Reset rate limit for key."""
        self._buckets.pop(key, None)


class ApiKeyRotator:
    """API key rotation manager.

    Supports multiple API keys per service with automatic rotation.
    """

    @dataclass(slots=True)
    class ApiKey:
        key_id: str
        key_hash: str
        created_at: float
        expires_at: float | None
        last_used: float | None
        is_active: bool

        @property
        def is_expired(self) -> bool:
            return self.expires_at is not None and self.expires_at < time.time()

    def __init__(self):
        self._keys: dict[str, ApiKeyRotator.ApiKey] = {}
        self._current_key_id: str | None = None

    @staticmethod
    def _hash_key(key_value: str) -> str:
        """Hash an API key for storage/verification."""
        if not key_value:
            raise ValueError("key_value cannot be empty")
        return hashlib.sha256(key_value.encode("utf-8")).hexdigest()

    def create_key(
        self,
        key_value: str,
        expires_in_seconds: float | None = None,
    ) -> str:
        """Create a new API key.

        Args:
            key_value: The actual API key value.
            expires_in_seconds: Optional expiration time.

        Returns:
            Key ID for referencing this key.
        """
        if expires_in_seconds is not None and expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be > 0 when provided")

        key_id = secrets.token_hex(16)
        key_hash = self._hash_key(key_value)
        now = time.time()

        self._keys[key_id] = self.ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            created_at=now,
            expires_at=now + expires_in_seconds if expires_in_seconds else None,
            last_used=None,
            is_active=True,
        )

        if self._current_key_id is None:
            self._current_key_id = key_id

        return key_id

    def verify_key(self, key_value: str) -> str | None:
        """Verify an API key and return its ID."""
        key_hash = self._hash_key(key_value)
        now = time.time()

        for key_id, key in self._keys.items():
            if not key.is_active:
                continue
            if key.expires_at is not None and key.expires_at < now:
                continue
            if hmac.compare_digest(key.key_hash, key_hash):
                key.last_used = now
                return key_id

        return None

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        key = self._keys.get(key_id)
        if key is None:
            return False

        key.is_active = False

        if self._current_key_id == key_id:
            self._current_key_id = self._find_next_active_key(exclude=key_id)

        return True

    def _find_next_active_key(self, exclude: str | None = None) -> str | None:
        """Find the next active, non-expired key."""
        now = time.time()
        candidates = [
            key.key_id
            for key in self._keys.values()
            if key.is_active and key.key_id != exclude and (key.expires_at is None or key.expires_at >= now)
        ]
        return candidates[0] if candidates else None

    def rotate_key(self) -> str | None:
        """Rotate to next active key.

        Returns:
            New current key ID, or None if no active keys are available.
        """
        now = time.time()
        active_keys = [
            key for key in self._keys.values()
            if key.is_active and (key.expires_at is None or key.expires_at >= now)
        ]

        if not active_keys:
            self._current_key_id = None
            return None

        active_keys.sort(key=lambda item: item.created_at)

        current_idx = -1
        if self._current_key_id is not None:
            for idx, key in enumerate(active_keys):
                if key.key_id == self._current_key_id:
                    current_idx = idx
                    break

        next_idx = (current_idx + 1) % len(active_keys)
        self._current_key_id = active_keys[next_idx].key_id
        return self._current_key_id

    def get_current_key(self) -> str | None:
        """Get current active key ID."""
        if self._current_key_id is None:
            return None

        key = self._keys.get(self._current_key_id)
        if key is None or not key.is_active or key.is_expired:
            self._current_key_id = self._find_next_active_key(exclude=self._current_key_id)
        return self._current_key_id

    def get_key_metadata(self, key_id: str) -> dict[str, Any] | None:
        """Get non-sensitive metadata for a key."""
        key = self._keys.get(key_id)
        if key is None:
            return None

        return {
            "key_id": key.key_id,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "last_used": key.last_used,
            "is_active": key.is_active,
            "is_expired": key.is_expired,
        }


class AuditSigner:
    """Cryptographic audit log signing.

    Signs audit entries to prevent tampering.
    """

    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._secret = secret_key.encode("utf-8")

    def sign(self, data: dict[str, Any]) -> str:
        """Sign audit entry data."""
        content = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hmac.new(self._secret, content.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, data: dict[str, Any], signature: str) -> bool:
        """Verify audit entry signature."""
        if not signature:
            return False
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)

    def sign_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Add signature to audit entry."""
        signed = dict(entry)
        signed["signature"] = self.sign(entry)
        signed["signed_at"] = time.time()
        return signed


class SecureAuditLog:
    """Audit log with cryptographic integrity.

    Combines signing with storage and verification.
    """

    def __init__(self, secret_key: str):
        self._signer = AuditSigner(secret_key)
        self._entries: list[dict[str, Any]] = []

    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Append signed entry to audit log."""
        base_entry = dict(entry)
        base_entry["entry_index"] = len(self._entries)
        base_entry["timestamp"] = base_entry.get("timestamp", time.time())

        signed_entry = self._signer.sign_entry(base_entry)
        self._entries.append(signed_entry)
        return dict(signed_entry)

    def verify(self) -> tuple[bool, list[int]]:
        """Verify all entries in audit log.

        Returns:
            Tuple of (all_valid, invalid_indices).
        """
        invalid: list[int] = []

        for index, entry in enumerate(self._entries):
            signature = entry.get("signature")
            unsigned_entry = {
                key: value
                for key, value in entry.items()
                if key not in {"signature", "signed_at"}
            }

            if not self._signer.verify(unsigned_entry, signature or ""):
                invalid.append(index)

        return (len(invalid) == 0, invalid)

    def get_entries(self) -> list[dict[str, Any]]:
        """Get all audit entries."""
        return [dict(entry) for entry in self._entries]
"""Security utilities for AICP.

Provides rate limiting, API key rotation, and audit signing.
"""

import hashlib
import hmac
import secrets
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded: {limit} requests per {window_seconds}s")


class RateLimiter:
    """Token bucket rate limiter.
    
    Implements token bucket algorithm for rate limiting.
    """
    
    def __init__(self, requests_per_window: int, window_seconds: float):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        
    def check(self, key: str, cost: int = 1) -> None:
        """Check if request is allowed.
        
        Args:
            key: Rate limit key (e.g., user_id, api_key)
            cost: Cost of this request (default: 1)
            
        Raises:
            RateLimitExceeded: If limit is exceeded.
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if t > window_start]
        
        if len(bucket) + cost > self.requests_per_window:
            raise RateLimitExceeded(self.requests_per_window, self.window_seconds)
            
        bucket.extend([now] * cost)
        
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key."""
        now = time.time()
        window_start = now - self.window_seconds
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if t > window_start]
        return max(0, self.requests_per_window - len(bucket))
        
    def reset(self, key: str) -> None:
        """Reset rate limit for key."""
        if key in self._buckets:
            del self._buckets[key]


class ApiKeyRotator:
    """API key rotation manager.
    
    Supports multiple API keys per service with automatic rotation.
    """
    
    @dataclass
    class ApiKey:
        key_id: str
        key_hash: str
        created_at: float
        expires_at: float | None
        last_used: float | None
        is_active: bool
        
    def __init__(self):
        self._keys: dict[str, "ApiKeyRotator.ApiKey"] = {}
        self._current_key_id: str | None = None
        
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
        key_id = secrets.token_hex(16)
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()[:16]
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
        """Verify an API key and return its ID.
        
        Args:
            key_value: The API key to verify.
            
        Returns:
            Key ID if valid, None otherwise.
        """
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()[:16]
        now = time.time()
        
        for key_id, key in self._keys.items():
            if key.key_hash == key_hash and key.is_active:
                if key.expires_at and key.expires_at < now:
                    return None
                key.last_used = now
                return key_id
        return None
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            return True
        return False
    
    def rotate_key(self) -> str | None:
        """Rotate to next active key.
        
        Returns:
            New current key ID, or None if no keys available.
        """
        keys = [k for k in self._keys.values() if k.is_active]
        if not keys:
            return None
            
        current_idx = 0
        if self._current_key_id:
            for i, k in enumerate(keys):
                if k.key_id == self._current_key_id:
                    current_idx = i
                    break
                    
        next_idx = (current_idx + 1) % len(keys)
        self._current_key_id = keys[next_idx].key_id
        return self._current_key_id
    
    def get_current_key(self) -> str | None:
        """Get current active key ID."""
        return self._current_key_id


class AuditSigner:
    """Cryptographic audit log signing.
    
    Signs audit entries to prevent tampering.
    """
    
    def __init__(self, secret_key: str):
        self._secret = secret_key.encode()
        
    def sign(self, data: dict[str, Any]) -> str:
        """Sign audit entry data.
        
        Args:
            data: Audit entry data to sign.
            
        Returns:
            HMAC signature.
        """
        import json
        content = json.dumps(data, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(self._secret, content.encode(), hashlib.sha256).hexdigest()
        return signature
    
    def verify(self, data: dict[str, Any], signature: str) -> bool:
        """Verify audit entry signature.
        
        Args:
            data: Audit entry data.
            signature: Expected signature.
            
        Returns:
            True if signature is valid.
        """
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)
    
    def sign_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Add signature to audit entry.
        
        Args:
            entry: Audit entry to sign.
            
        Returns:
            Entry with signature added.
        """
        signed = entry.copy()
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
        """Append signed entry to audit log.
        
        Args:
            entry: Audit entry to append.
            
        Returns:
            Signed entry with signature.
        """
        entry["entry_index"] = len(self._entries)
        entry["timestamp"] = entry.get("timestamp", time.time())
        
        signed_entry = self._signer.sign_entry(entry)
        self._entries.append(signed_entry)
        return signed_entry
    
    def verify(self) -> tuple[bool, list[int]]:
        """Verify all entries in audit log.
        
        Returns:
            Tuple of (all_valid, invalid_indices).
        """
        invalid = []
        
        for i, entry in enumerate(self._entries):
            signature = entry.pop("signature", None)
            signed_at = entry.pop("signed_at", None)
            
            if not self._signer.verify(entry, signature or ""):
                invalid.append(i)
                
            entry["signature"] = signature
            entry["signed_at"] = signed_at
            
        return (len(invalid) == 0, invalid)
    
    def get_entries(self) -> list[dict[str, Any]]:
        """Get all audit entries."""
        return self._entries.copy()

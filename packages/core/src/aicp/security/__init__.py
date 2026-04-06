from __future__ import annotations

from importlib import import_module

from .ssrf import (
    SSRFBlockedError,
    SSRFPolicy,
    check_ssrf_safe,
    is_blocked_hostname,
    is_blocked_hostname_or_ip,
    is_private_ip_address,
    validate_and_resolve_hostname,
    validate_url,
)

_encryption = import_module("aicp.security.encryption")

CredentialEncryptor = _encryption.CredentialEncryptor
EncryptedCredential = _encryption.EncryptedCredential
EncryptionAuditLog = _encryption.EncryptionAuditLog
EncryptionError = _encryption.EncryptionError
InMemoryKMSClient = _encryption.InMemoryKMSClient
scope_key = _encryption.scope_key

__all__ = [
    "SSRFBlockedError",
    "SSRFPolicy",
    "CredentialEncryptor",
    "EncryptedCredential",
    "EncryptionAuditLog",
    "EncryptionError",
    "InMemoryKMSClient",
    "scope_key",
    "is_private_ip_address",
    "is_blocked_hostname",
    "is_blocked_hostname_or_ip",
    "validate_url",
    "validate_and_resolve_hostname",
    "check_ssrf_safe",
]

from __future__ import annotations

import base64
import binascii
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from hmac import digest as hmac_digest
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aicp.errors import AicpError

_DATA_NONCE_BYTES = 12
_WRAP_NONCE_BYTES = 12
_GCM_TAG_BYTES = 16
_AES_KEY_BYTES = 32
_PBKDF2_ITERATIONS = 390_000
_ENV_KEK_ID = "env:default"


class EncryptionError(AicpError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "encryption_error",
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details, cause=cause)


@dataclass(frozen=True)
class EncryptedCredential:
    encrypted_dek: str
    kek_id: str
    iv: str
    tag: str
    ciphertext: str

    def to_dict(self) -> dict[str, str]:
        return {
            "encrypted_dek": self.encrypted_dek,
            "kek_id": self.kek_id,
            "iv": self.iv,
            "tag": self.tag,
            "ciphertext": self.ciphertext,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EncryptedCredential":
        required_fields = {"encrypted_dek", "kek_id", "iv", "tag", "ciphertext"}
        missing_fields = required_fields.difference(data)
        if missing_fields:
            raise EncryptionError(
                "Encrypted credential is missing required fields",
                code="invalid_envelope",
                details={"missing_fields": sorted(missing_fields)},
            )
        return cls(
            encrypted_dek=data["encrypted_dek"],
            kek_id=data["kek_id"],
            iv=data["iv"],
            tag=data["tag"],
            ciphertext=data["ciphertext"],
        )

    @classmethod
    def from_json(cls, payload: str) -> "EncryptedCredential":
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise EncryptionError("Encrypted credential JSON is invalid", code="invalid_envelope", cause=exc) from exc
        if not isinstance(raw, dict):
            raise EncryptionError("Encrypted credential JSON must be an object", code="invalid_envelope")
        return cls.from_dict(raw)


class EncryptionAuditLog:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record(self, operation: str, scope: str, key_id: str, success: bool) -> None:
        self.entries.append(
            {
                "operation": operation,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scope": scope,
                "key_id": key_id,
                "success": success,
            }
        )


class InMemoryKMSClient:
    def __init__(self, keys: dict[str, bytes], active_kek_id: str) -> None:
        self._keys = dict(keys)
        self.active_kek_id = active_kek_id

    def resolve_key(self, kek_id: str) -> bytes:
        try:
            key = self._keys[kek_id]
        except KeyError as exc:
            raise EncryptionError(
                f"Unknown KEK id: {kek_id}",
                code="unknown_kek_id",
                details={"kek_id": kek_id},
                cause=exc,
            ) from exc
        if len(key) != _AES_KEY_BYTES:
            raise EncryptionError(
                "KEK must be 32 bytes for AES-256-GCM",
                code="invalid_kek",
                details={"kek_id": kek_id, "length": len(key)},
            )
        return key


def scope_key(plaintext: bytes, scope: str) -> bytes:
    if not plaintext:
        raise EncryptionError("Scope derivation requires non-empty key material", code="invalid_scope_key_material")
    if not scope:
        raise EncryptionError("Scope is required for key derivation", code="invalid_scope")
    return hmac_digest(plaintext, scope.encode("utf-8"), "sha256")


class CredentialEncryptor:
    def __init__(
        self,
        *,
        kms_client: InMemoryKMSClient | None = None,
        audit_log: EncryptionAuditLog | None = None,
    ) -> None:
        self._kms_client = kms_client
        self._audit_log = audit_log or EncryptionAuditLog()
        self._seen_nonces: set[bytes] = set()

    @property
    def audit_log(self) -> EncryptionAuditLog:
        return self._audit_log

    def encrypt(
        self,
        plaintext: bytes,
        *,
        scope: str,
        kek_id: str | None = None,
        nonce: bytes | None = None,
    ) -> EncryptedCredential:
        active_kek_id = kek_id or self._get_active_kek_id()
        try:
            dek = os.urandom(_AES_KEY_BYTES)
            iv = nonce if nonce is not None else secrets.token_bytes(_DATA_NONCE_BYTES)
            self._validate_nonce(iv)
            self._remember_nonce(iv)
            scoped_dek = scope_key(dek, scope)
            ciphertext_with_tag = AESGCM(scoped_dek).encrypt(iv, plaintext, scope.encode("utf-8"))
            ciphertext = ciphertext_with_tag[:-_GCM_TAG_BYTES]
            tag = ciphertext_with_tag[-_GCM_TAG_BYTES:]
            wrapped_dek = self._wrap_dek(dek, active_kek_id)
            self._record("encrypt", scope, active_kek_id, True)
            return EncryptedCredential(
                encrypted_dek=_b64encode(wrapped_dek),
                kek_id=active_kek_id,
                iv=_b64encode(iv),
                tag=_b64encode(tag),
                ciphertext=_b64encode(ciphertext),
            )
        except EncryptionError:
            self._record("encrypt", scope, active_kek_id, False)
            raise
        except Exception as exc:
            self._record("encrypt", scope, active_kek_id, False)
            raise EncryptionError("Credential encryption failed", cause=exc) from exc

    def decrypt(self, envelope: EncryptedCredential, *, scope: str) -> bytes:
        try:
            wrapped_dek = _b64decode(envelope.encrypted_dek, field_name="encrypted_dek")
            dek = self._unwrap_dek(wrapped_dek, envelope.kek_id)
            scoped_dek = scope_key(dek, scope)
            iv = _b64decode(envelope.iv, field_name="iv")
            tag = _b64decode(envelope.tag, field_name="tag")
            ciphertext = _b64decode(envelope.ciphertext, field_name="ciphertext")
            self._validate_nonce(iv)
            plaintext = AESGCM(scoped_dek).decrypt(iv, ciphertext + tag, scope.encode("utf-8"))
            self._record("decrypt", scope, envelope.kek_id, True)
            return plaintext
        except EncryptionError:
            self._record("decrypt", scope, envelope.kek_id, False)
            raise
        except InvalidTag as exc:
            self._record("decrypt", scope, envelope.kek_id, False)
            raise EncryptionError("Credential decryption failed", code="decryption_failed", cause=exc) from exc
        except Exception as exc:
            self._record("decrypt", scope, envelope.kek_id, False)
            raise EncryptionError("Credential decryption failed", code="decryption_failed", cause=exc) from exc

    def rotate_kek(
        self,
        envelope: EncryptedCredential,
        *,
        scope: str,
        new_kek_id: str | None = None,
    ) -> EncryptedCredential:
        target_kek_id = new_kek_id or self._get_active_kek_id()
        try:
            wrapped_dek = _b64decode(envelope.encrypted_dek, field_name="encrypted_dek")
            dek = self._unwrap_dek(wrapped_dek, envelope.kek_id)
            rotated = EncryptedCredential(
                encrypted_dek=_b64encode(self._wrap_dek(dek, target_kek_id)),
                kek_id=target_kek_id,
                iv=envelope.iv,
                tag=envelope.tag,
                ciphertext=envelope.ciphertext,
            )
            self._record("rotate", scope, target_kek_id, True)
            return rotated
        except EncryptionError:
            self._record("rotate", scope, target_kek_id, False)
            raise
        except Exception as exc:
            self._record("rotate", scope, target_kek_id, False)
            raise EncryptionError("DEK rotation failed", code="rotation_failed", cause=exc) from exc

    def dispose_dek(self, dek: bytearray, *, scope: str, key_id: str) -> None:
        for index in range(len(dek)):
            dek[index] = 0
        self._record("dispose", scope, key_id, True)

    def _record(self, operation: str, scope: str, key_id: str, success: bool) -> None:
        self._audit_log.record(operation=operation, scope=scope, key_id=key_id, success=success)

    def _get_active_kek_id(self) -> str:
        if self._kms_client is not None:
            return self._kms_client.active_kek_id
        return _ENV_KEK_ID

    def _resolve_kek(self, kek_id: str) -> bytes:
        if self._kms_client is not None:
            return self._kms_client.resolve_key(kek_id)

        master_key = os.getenv("AICP_MASTER_KEY")
        if not master_key:
            raise EncryptionError(
                "AICP_MASTER_KEY environment variable is required when no KMS client is configured",
                code="missing_master_key",
            )
        return pbkdf2_hmac(
            "sha256",
            master_key.encode("utf-8"),
            f"aicp:kek:{kek_id}".encode("utf-8"),
            _PBKDF2_ITERATIONS,
            dklen=_AES_KEY_BYTES,
        )

    def _wrap_dek(self, dek: bytes, kek_id: str) -> bytes:
        kek = self._resolve_kek(kek_id)
        wrap_iv = secrets.token_bytes(_WRAP_NONCE_BYTES)
        wrapped = AESGCM(kek).encrypt(wrap_iv, dek, kek_id.encode("utf-8"))
        return wrap_iv + wrapped

    def _unwrap_dek(self, wrapped_dek: bytes, kek_id: str) -> bytes:
        if len(wrapped_dek) <= _WRAP_NONCE_BYTES:
            raise EncryptionError("Wrapped DEK payload is too short", code="invalid_wrapped_dek")
        kek = self._resolve_kek(kek_id)
        wrap_iv = wrapped_dek[:_WRAP_NONCE_BYTES]
        wrapped_payload = wrapped_dek[_WRAP_NONCE_BYTES:]
        try:
            dek = AESGCM(kek).decrypt(wrap_iv, wrapped_payload, kek_id.encode("utf-8"))
        except InvalidTag as exc:
            raise EncryptionError("Unable to unwrap DEK", code="invalid_kek", cause=exc) from exc
        if len(dek) != _AES_KEY_BYTES:
            raise EncryptionError("Unwrapped DEK must be 32 bytes", code="invalid_dek")
        return dek

    def _validate_nonce(self, nonce: bytes) -> None:
        if len(nonce) != _DATA_NONCE_BYTES:
            raise EncryptionError(
                "AES-GCM nonce must be exactly 12 bytes",
                code="invalid_nonce",
                details={"length": len(nonce)},
            )

    def _remember_nonce(self, nonce: bytes) -> None:
        if nonce in self._seen_nonces:
            raise EncryptionError("Nonce reuse detected", code="nonce_reuse")
        self._seen_nonces.add(nonce)


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: str, *, field_name: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error as exc:
        raise EncryptionError(
            f"Field '{field_name}' is not valid base64",
            code="invalid_base64",
            details={"field": field_name},
            cause=exc,
        ) from exc

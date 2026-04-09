import base64
import json

import pytest

from aicp.security import (
    CredentialEncryptor,
    EncryptedCredential,
    EncryptionAuditLog,
    EncryptionError,
    InMemoryKMSClient,
    scope_key,
)


def _set_master_key(monkeypatch: pytest.MonkeyPatch, value: str = "unit-test-master-key") -> None:
    monkeypatch.setenv("AICP_MASTER_KEY", value)


class TestScopeKey:
    def test_returns_32_bytes(self):
        derived = scope_key(b"plain-secret", "tenant-a/user-a/capability.read")

        assert len(derived) == 32

    def test_is_scope_sensitive(self):
        first = scope_key(b"plain-secret", "tenant-a/user-a/capability.read")
        second = scope_key(b"plain-secret", "tenant-b/user-a/capability.read")

        assert first != second


class TestCredentialEncryptor:
    def test_encrypt_decrypt_round_trip_with_env_key(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()

        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        assert encryptor.decrypt(envelope, scope="tenant-a/user-a/openai.chat") == b"sk-live-123"

    def test_encrypt_decrypt_round_trip_with_kms_client(self):
        kms_client = InMemoryKMSClient({"kms-v1": b"k" * 32}, active_kek_id="kms-v1")
        encryptor = CredentialEncryptor(kms_client=kms_client)

        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        assert encryptor.decrypt(envelope, scope="tenant-a/user-a/openai.chat") == b"sk-live-123"

    def test_encrypt_returns_base64_encoded_fields(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()

        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        for value in envelope.to_dict().values():
            if value == envelope.kek_id:
                continue
            assert isinstance(value, str)
            base64.b64decode(value, validate=True)

    def test_to_json_and_from_json_round_trip(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()

        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")
        serialized = envelope.to_json()

        restored = EncryptedCredential.from_json(serialized)

        assert restored == envelope
        assert json.loads(serialized)["kek_id"] == envelope.kek_id

    def test_wrong_scope_fails_decryption(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()
        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        with pytest.raises(EncryptionError):
            encryptor.decrypt(envelope, scope="tenant-a/user-b/openai.chat")

    def test_missing_master_key_env_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("AICP_MASTER_KEY", raising=False)
        encryptor = CredentialEncryptor()

        with pytest.raises(EncryptionError):
            encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

    def test_wrong_master_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch, "master-key-one")
        encryptor = CredentialEncryptor()
        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        _set_master_key(monkeypatch, "master-key-two")

        with pytest.raises(EncryptionError):
            encryptor.decrypt(envelope, scope="tenant-a/user-a/openai.chat")

    def test_invalid_base64_payload_raises(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()
        envelope = EncryptedCredential(
            encrypted_dek="%%%",
            kek_id="env:default",
            iv=base64.b64encode(b"1" * 12).decode("ascii"),
            tag=base64.b64encode(b"2" * 16).decode("ascii"),
            ciphertext=base64.b64encode(b"3" * 8).decode("ascii"),
        )

        with pytest.raises(EncryptionError):
            encryptor.decrypt(envelope, scope="tenant-a/user-a/openai.chat")

    def test_unknown_kms_key_raises(self):
        kms_client = InMemoryKMSClient({"kms-v1": b"k" * 32}, active_kek_id="kms-v1")
        encryptor = CredentialEncryptor(kms_client=kms_client)

        with pytest.raises(EncryptionError):
            encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat", kek_id="kms-missing")

    def test_rejects_invalid_nonce_length(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()

        with pytest.raises(EncryptionError):
            encryptor.encrypt(
                b"sk-live-123",
                scope="tenant-a/user-a/openai.chat",
                nonce=b"short",
            )

    def test_rejects_nonce_reuse(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        encryptor = CredentialEncryptor()
        nonce = b"1" * 12

        encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat", nonce=nonce)

        with pytest.raises(EncryptionError):
            encryptor.encrypt(b"sk-live-456", scope="tenant-a/user-a/openai.chat", nonce=nonce)

    def test_rotate_kek_rewraps_dek_and_preserves_ciphertext(self):
        kms_client = InMemoryKMSClient(
            {"kms-v1": b"k" * 32, "kms-v2": b"z" * 32},
            active_kek_id="kms-v1",
        )
        encryptor = CredentialEncryptor(kms_client=kms_client)
        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        rotated = encryptor.rotate_kek(
            envelope,
            scope="tenant-a/user-a/openai.chat",
            new_kek_id="kms-v2",
        )

        assert rotated.kek_id == "kms-v2"
        assert rotated.encrypted_dek != envelope.encrypted_dek
        assert rotated.iv == envelope.iv
        assert rotated.tag == envelope.tag
        assert rotated.ciphertext == envelope.ciphertext

    def test_rotated_envelope_decrypts_with_new_key(self):
        kms_client = InMemoryKMSClient(
            {"kms-v1": b"k" * 32, "kms-v2": b"z" * 32},
            active_kek_id="kms-v1",
        )
        encryptor = CredentialEncryptor(kms_client=kms_client)
        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        rotated = encryptor.rotate_kek(
            envelope,
            scope="tenant-a/user-a/openai.chat",
            new_kek_id="kms-v2",
        )

        assert encryptor.decrypt(rotated, scope="tenant-a/user-a/openai.chat") == b"sk-live-123"

    def test_original_envelope_remains_decryptable_after_rotation(self):
        kms_client = InMemoryKMSClient(
            {"kms-v1": b"k" * 32, "kms-v2": b"z" * 32},
            active_kek_id="kms-v1",
        )
        encryptor = CredentialEncryptor(kms_client=kms_client)
        original = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        encryptor.rotate_kek(original, scope="tenant-a/user-a/openai.chat", new_kek_id="kms-v2")

        assert encryptor.decrypt(original, scope="tenant-a/user-a/openai.chat") == b"sk-live-123"

    def test_audit_log_records_encrypt_decrypt_and_rotate(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        audit_log = EncryptionAuditLog()
        encryptor = CredentialEncryptor(audit_log=audit_log)

        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")
        encryptor.decrypt(envelope, scope="tenant-a/user-a/openai.chat")
        encryptor.rotate_kek(envelope, scope="tenant-a/user-a/openai.chat")

        assert [entry["operation"] for entry in audit_log.entries] == ["encrypt", "decrypt", "rotate"]
        assert all(entry["success"] is True for entry in audit_log.entries)

    def test_audit_log_records_failures(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        audit_log = EncryptionAuditLog()
        encryptor = CredentialEncryptor(audit_log=audit_log)
        envelope = encryptor.encrypt(b"sk-live-123", scope="tenant-a/user-a/openai.chat")

        with pytest.raises(EncryptionError):
            encryptor.decrypt(envelope, scope="tenant-a/user-b/openai.chat")

        assert audit_log.entries[-1]["operation"] == "decrypt"
        assert audit_log.entries[-1]["success"] is False

    def test_dispose_dek_zeroizes_material_and_logs(self, monkeypatch: pytest.MonkeyPatch):
        _set_master_key(monkeypatch)
        audit_log = EncryptionAuditLog()
        encryptor = CredentialEncryptor(audit_log=audit_log)
        dek = bytearray(b"x" * 32)

        encryptor.dispose_dek(dek, scope="tenant-a/user-a/openai.chat", key_id="env:default")

        assert dek == bytearray(b"\x00" * 32)
        assert audit_log.entries[-1]["operation"] == "dispose"
        assert audit_log.entries[-1]["success"] is True

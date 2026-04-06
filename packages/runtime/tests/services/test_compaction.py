import json
from typing import Any

import pytest

from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.services.audit import AuditService
from aicp_runtime.services.compaction import CompactionConfig, CompactionMode, CompactionService


def _message(text: str, *, role: str = "assistant", **extra: object) -> dict[str, Any]:
    return {"type": "message", "role": role, "content": text, **extra}


def _approval_event() -> dict[str, Any]:
    return {
        "type": "approval_request",
        "approval_request_id": "appr_123",
        "content": "Approve wire transfer",
    }


def _policy_event() -> dict[str, Any]:
    return {
        "type": "policy_change",
        "policy_name": "high_risk_default",
        "content": "Raised risk threshold",
    }


def _capability_output() -> dict[str, Any]:
    return {
        "type": "capability_output",
        "capability_name": "payments.transfer",
        "output": {"transfer_id": "tr_123", "status": "success"},
    }


def _audit_entry() -> dict[str, Any]:
    return {
        "id": "audit_123",
        "event_type": "execution_complete",
        "actor": "agent",
        "content": "Execution finished",
    }


def _decision_entry() -> dict[str, Any]:
    return {
        "type": "decision",
        "decision": "Use provider fallback",
        "rationale": "Primary endpoint is degraded",
    }


def _session(messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": "sess_ctx_123",
        "status": "active",
        "trust_tier": 2,
        "created_at": "2026-04-05T00:00:00Z",
        "updated_at": "2026-04-05T00:00:00Z",
        "context": {"messages": messages or []},
        "memory": {"episodic": []},
        "metadata": {},
    }


@pytest.fixture
def store() -> InMemoryRuntimeStore:
    return InMemoryRuntimeStore()


@pytest.fixture
def audit_service(store: InMemoryRuntimeStore) -> AuditService:
    return AuditService(runtime_store=store)


@pytest.fixture
def service(store: InMemoryRuntimeStore, audit_service: AuditService) -> CompactionService:
    return CompactionService(runtime_store=store, audit_service=audit_service)


async def _save_session(store: InMemoryRuntimeStore, session: dict[str, Any]) -> None:
    await store.save_session_state(session)


@pytest.mark.asyncio
async def test_aggressive_mode_compacts_low_signal_messages(service: CompactionService) -> None:
    entry = _message("hello there", role="user")

    compacted = service.compact_entry(entry, mode=CompactionMode.AGGRESSIVE)

    assert compacted["type"] == "compacted_summary"
    assert compacted["compaction"]["mode"] == "aggressive"


@pytest.mark.asyncio
async def test_balanced_mode_preserves_decision_entries(service: CompactionService) -> None:
    preserved = service.preserve_entry(_decision_entry(), reason="decision")

    assert preserved["compaction"]["preserved"] is True
    assert preserved["decision"] == "Use provider fallback"


@pytest.mark.asyncio
async def test_preserve_mode_only_compacts_obvious_redundancy(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(default_mode=CompactionMode.PRESERVE, token_limit=20),
    )
    session = _session(
        [
            _message("ok"),
            _message("ok"),
            _message("unique but low signal"),
        ]
    )
    await _save_session(store, session)

    result = await service.compact_session(session["id"], force=True)
    saved = await store.get_session_state(session["id"])

    assert result.compacted_entries == 2
    assert saved is not None
    assert len(saved["context"]["messages"]) == 2
    assert saved["context"]["messages"][1]["content"] == "unique but low signal"


@pytest.mark.asyncio
async def test_approvals_are_never_compacted(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("hello"), _approval_event(), _message("thanks")])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=10),
    )

    await service.compact_session(session["id"], force=True)
    saved = await store.get_session_state(session["id"])

    assert saved is not None
    assert any(item.get("approval_request_id") == "appr_123" for item in saved["context"]["messages"])


@pytest.mark.asyncio
async def test_policy_changes_are_never_compacted(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("hello"), _policy_event(), _message("ok")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    await service.compact_session(session["id"], force=True, mode=CompactionMode.AGGRESSIVE)
    saved = await store.get_session_state(session["id"])

    assert saved is not None
    assert any(item.get("policy_name") == "high_risk_default" for item in saved["context"]["messages"])


@pytest.mark.asyncio
async def test_capability_outputs_are_never_compacted(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("noted"), _capability_output(), _message("done")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    await service.compact_session(session["id"], force=True)
    saved = await store.get_session_state(session["id"])

    assert saved is not None
    assert any(item.get("capability_name") == "payments.transfer" for item in saved["context"]["messages"])


@pytest.mark.asyncio
async def test_audit_entries_are_never_compacted(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("hello"), _audit_entry(), _message("confirmed")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    await service.compact_session(session["id"], force=True)
    saved = await store.get_session_state(session["id"])

    assert saved is not None
    assert any(item.get("id") == "audit_123" for item in saved["context"]["messages"])


@pytest.mark.asyncio
async def test_budget_status_reports_under_threshold(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("short")])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=1000, trigger_ratio=0.8),
    )

    status = await service.get_budget_status(session["id"])

    assert status.used_tokens < status.threshold_tokens
    assert status.should_compact is False


@pytest.mark.asyncio
async def test_budget_status_reports_at_threshold(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    content = "x" * 320
    session = _session([_message(content)])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=100, trigger_ratio=0.8),
    )

    status = await service.get_budget_status(session["id"])

    assert status.used_tokens >= status.threshold_tokens
    assert status.should_compact is True


@pytest.mark.asyncio
async def test_budget_status_reports_over_threshold(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("x" * 600)])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=100, trigger_ratio=0.8),
    )

    status = await service.get_budget_status(session["id"])

    assert status.used_tokens > status.threshold_tokens
    assert status.should_compact is True


@pytest.mark.asyncio
async def test_set_budget_limit_persists_session_override(service: CompactionService, store: InMemoryRuntimeStore) -> None:
    session = _session([_message("hello")])
    await _save_session(store, session)

    updated = await service.set_budget_limit(session["id"], 2048)
    saved = await store.get_session_state(session["id"])

    assert updated.token_limit == 2048
    assert saved is not None
    assert saved["metadata"]["compaction"]["token_limit"] == 2048


@pytest.mark.asyncio
async def test_estimate_compaction_reports_savings(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("ok"), _message("ok"), _message("ok")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    result = await service.estimate_compaction(session["id"], mode=CompactionMode.AGGRESSIVE)

    assert result.before_tokens > result.after_tokens
    assert result.savings_pct > 0


@pytest.mark.asyncio
async def test_compact_session_persists_compacted_state(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("hello"), _message("ok"), _message("thanks")])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=10),
    )

    result = await service.compact_session(session["id"], force=True)
    saved = await store.get_session_state(session["id"])

    assert result.compacted_entries >= 1
    assert saved is not None
    assert any(item.get("type") == "compacted_summary" for item in saved["context"]["messages"])


@pytest.mark.asyncio
async def test_compact_session_skips_when_under_threshold(service: CompactionService, store: InMemoryRuntimeStore) -> None:
    session = _session([_message("brief")])
    await _save_session(store, session)

    result = await service.compact_session(session["id"], force=False)

    assert result.before_tokens == result.after_tokens
    assert result.compacted_entries == 0


@pytest.mark.asyncio
async def test_force_compaction_runs_below_threshold(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("ok"), _message("ok")])
    await _save_session(store, session)
    service = CompactionService(
        runtime_store=store,
        audit_service=audit_service,
        config=CompactionConfig(token_limit=1000),
    )

    result = await service.compact_session(session["id"], force=True)

    assert result.compacted_entries == 2


@pytest.mark.asyncio
async def test_empty_session_is_a_noop(service: CompactionService, store: InMemoryRuntimeStore) -> None:
    session = _session([])
    await _save_session(store, session)

    result = await service.compact_session(session["id"], force=True)

    assert result.before_tokens == result.after_tokens
    assert result.preserved_entries == 0
    assert result.compacted_entries == 0


@pytest.mark.asyncio
async def test_multiple_compaction_passes_do_not_over_compact(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("ok"), _message("ok"), _decision_entry()])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    first = await service.compact_session(session["id"], force=True)
    second = await service.compact_session(session["id"], force=True)

    assert first.compacted_entries > 0
    assert second.compacted_entries == 0


@pytest.mark.asyncio
async def test_preserve_entry_marks_metadata(service: CompactionService) -> None:
    preserved = service.preserve_entry(_approval_event(), reason="approval")

    assert preserved["compaction"]["preserved"] is True
    assert preserved["compaction"]["reason"] == "approval"


@pytest.mark.asyncio
async def test_compact_entry_marks_summary_metadata(service: CompactionService) -> None:
    compacted = service.compact_entry(_message("thanks"), mode=CompactionMode.BALANCED)

    assert compacted["compaction"]["compacted"] is True
    assert compacted["content"]


@pytest.mark.asyncio
async def test_compaction_event_is_audited(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("ok"), _message("ok")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    result = await service.compact_session(session["id"], force=True)
    entries = await store.list_audit_entries()

    assert result.after_tokens < result.before_tokens
    assert any(entry["event_type"] == "session_compacted" for entry in entries)
    assert any(entry.get("metadata", {}).get("after_tokens") == result.after_tokens for entry in entries)


@pytest.mark.asyncio
async def test_compact_session_raises_for_missing_session(service: CompactionService) -> None:
    with pytest.raises(ValueError, match="Session not found"):
        await service.compact_session("missing-session", force=True)


@pytest.mark.asyncio
async def test_set_budget_limit_rejects_invalid_values(service: CompactionService, store: InMemoryRuntimeStore) -> None:
    session = _session([_message("hello")])
    await _save_session(store, session)

    with pytest.raises(ValueError, match="token_limit"):
        await service.set_budget_limit(session["id"], 0)


@pytest.mark.asyncio
async def test_session_specific_budget_override_affects_status(
    service: CompactionService, store: InMemoryRuntimeStore
) -> None:
    session = _session([_message("x" * 320)])
    await _save_session(store, session)
    await service.set_budget_limit(session["id"], 500)

    status = await service.get_budget_status(session["id"])

    assert status.token_limit == 500
    assert status.should_compact is False


@pytest.mark.asyncio
async def test_repetitive_low_signal_entries_collapse_to_single_summary(
    store: InMemoryRuntimeStore, audit_service: AuditService
) -> None:
    session = _session([_message("ok"), _message("ok"), _message("ok"), _message("ok")])
    await _save_session(store, session)
    service = CompactionService(runtime_store=store, audit_service=audit_service)

    await service.compact_session(session["id"], force=True, mode=CompactionMode.AGGRESSIVE)
    saved = await store.get_session_state(session["id"])

    assert saved is not None
    assert saved["context"]["messages"] == [saved["context"]["messages"][0]]
    assert saved["context"]["messages"][0]["type"] == "compacted_summary"


def test_compaction_schema_defines_expected_modes() -> None:
    with open("/Users/abhishekjha/CODE/AICP/spec/schemas/compaction.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)

    assert schema["properties"]["default_mode"]["enum"] == ["aggressive", "balanced", "preserve"]
    assert schema["properties"]["token_limit"]["default"] == 100000

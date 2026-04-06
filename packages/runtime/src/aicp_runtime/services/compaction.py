from __future__ import annotations

from copy import deepcopy
from enum import Enum
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.audit import AuditService


class CompactionMode(str, Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    PRESERVE = "preserve"


class CompactionConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    token_limit: int = Field(default=100_000, ge=1)
    trigger_ratio: float = Field(default=0.8, gt=0.0, le=1.0)
    default_mode: CompactionMode = CompactionMode.BALANCED
    min_entries: int = Field(default=1, ge=0)
    preserve_event_types: list[str] = Field(
        default_factory=lambda: [
            "approval_request",
            "approval_decision",
            "policy_change",
            "capability_output",
            "audit_entry",
            "compacted_summary",
        ]
    )


class CompactionResult(BaseModel):
    before_tokens: int = Field(ge=0)
    after_tokens: int = Field(ge=0)
    savings_pct: float = Field(ge=0.0, le=100.0)
    preserved_entries: int = Field(ge=0)
    compacted_entries: int = Field(ge=0)


class BudgetStatus(BaseModel):
    token_limit: int = Field(ge=1)
    threshold_tokens: int = Field(ge=0)
    used_tokens: int = Field(ge=0)
    remaining_tokens: int
    should_compact: bool
    mode: CompactionMode


class BudgetLimitUpdate(BaseModel):
    session_id: str
    token_limit: int = Field(ge=1)
    updated_at: str


class CompactionEvent(BaseModel):
    before_tokens: int = Field(ge=0)
    after_tokens: int = Field(ge=0)
    before_size_bytes: int = Field(ge=0)
    after_size_bytes: int = Field(ge=0)
    preserved_keys: list[str] = Field(default_factory=list)


class CompactionService:

    def __init__(
        self,
        runtime_store: RuntimeStore,
        audit_service: AuditService | None = None,
        config: CompactionConfig | None = None,
    ) -> None:
        self._store = runtime_store
        self._audit = audit_service
        self._config = config or CompactionConfig()

    async def compact_session(
        self,
        session_id: str,
        *,
        force: bool = False,
        mode: CompactionMode | None = None,
    ) -> CompactionResult:
        normalized_session_id = self._require_text(session_id, "session_id")
        session = await self._load_session(normalized_session_id)
        active_mode = mode or self._session_mode(session)
        messages = self._message_entries(session)
        before_tokens = self._estimate_tokens(messages)

        status = self._build_budget_status(session=session, mode=active_mode)
        if not force and not status.should_compact:
            return CompactionResult(
                before_tokens=before_tokens,
                after_tokens=before_tokens,
                savings_pct=0.0,
                preserved_entries=0,
                compacted_entries=0,
            )

        compacted_messages, preserved_entries, compacted_entries = self._compact_entries(
            messages,
            mode=active_mode,
        )
        after_tokens = self._estimate_tokens(compacted_messages)
        session.setdefault("context", {})["messages"] = compacted_messages
        session.setdefault("metadata", {})["compaction"] = {
            **self._session_compaction_metadata(session),
            "last_compacted_at": utc_now_rfc3339(),
            "last_mode": active_mode.value,
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
        }
        session["updated_at"] = utc_now_rfc3339()
        await self._store.save_session_state(session)

        result = CompactionResult(
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            savings_pct=self._savings_pct(before_tokens, after_tokens),
            preserved_entries=preserved_entries,
            compacted_entries=compacted_entries,
        )
        await self._append_audit(session=session, result=result, entries=compacted_messages)
        return result

    async def estimate_compaction(
        self,
        session_id: str,
        *,
        mode: CompactionMode | None = None,
    ) -> CompactionResult:
        normalized_session_id = self._require_text(session_id, "session_id")
        session = await self._load_session(normalized_session_id)
        messages = self._message_entries(session)
        active_mode = mode or self._session_mode(session)
        compacted_messages, preserved_entries, compacted_entries = self._compact_entries(
            messages,
            mode=active_mode,
        )
        before_tokens = self._estimate_tokens(messages)
        after_tokens = self._estimate_tokens(compacted_messages)
        return CompactionResult(
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            savings_pct=self._savings_pct(before_tokens, after_tokens),
            preserved_entries=preserved_entries,
            compacted_entries=compacted_entries,
        )

    async def get_budget_status(self, session_id: str) -> BudgetStatus:
        normalized_session_id = self._require_text(session_id, "session_id")
        session = await self._load_session(normalized_session_id)
        return self._build_budget_status(session=session, mode=self._session_mode(session))

    async def set_budget_limit(self, session_id: str, token_limit: int) -> BudgetLimitUpdate:
        normalized_session_id = self._require_text(session_id, "session_id")
        if token_limit < 1:
            raise ValueError("token_limit must be greater than 0")
        session = await self._load_session(normalized_session_id)
        compaction = self._session_compaction_metadata(session)
        compaction["token_limit"] = token_limit
        session.setdefault("metadata", {})["compaction"] = compaction
        session["updated_at"] = utc_now_rfc3339()
        await self._store.save_session_state(session)
        return BudgetLimitUpdate(
            session_id=normalized_session_id,
            token_limit=token_limit,
            updated_at=session["updated_at"],
        )

    def compact_entry(
        self,
        entry: dict[str, Any],
        *,
        mode: CompactionMode,
    ) -> dict[str, Any]:
        summary = self._summarize_entry(entry, mode)
        return {
            "type": "compacted_summary",
            "content": summary,
            "compaction": {
                "compacted": True,
                "mode": mode.value,
            },
        }

    def preserve_entry(self, entry: dict[str, Any], *, reason: str) -> dict[str, Any]:
        preserved = deepcopy(entry)
        preserved["compaction"] = {
            "preserved": True,
            "reason": reason,
        }
        return preserved

    def _compact_entries(
        self,
        entries: list[dict[str, Any]],
        *,
        mode: CompactionMode,
    ) -> tuple[list[dict[str, Any]], int, int]:
        preserved_count = 0
        compacted_count = 0
        compacted_entries: list[dict[str, Any]] = []
        run: list[dict[str, Any]] = []

        for entry in entries:
            if self._should_preserve(entry):
                if run:
                    replacements, run_count = self._flush_run(run, mode=mode)
                    compacted_entries.extend(replacements)
                    compacted_count += run_count
                    run = []
                compacted_entries.append(self.preserve_entry(entry, reason="invariant"))
                preserved_count += 1
                continue

            if self._is_already_compacted(entry):
                if run:
                    replacements, run_count = self._flush_run(run, mode=mode)
                    compacted_entries.extend(replacements)
                    compacted_count += run_count
                    run = []
                compacted_entries.append(deepcopy(entry))
                continue

            if self._should_compact(entry, mode):
                run.append(entry)
                continue

            if run:
                replacements, run_count = self._flush_run(run, mode=mode)
                compacted_entries.extend(replacements)
                compacted_count += run_count
                run = []
            compacted_entries.append(deepcopy(entry))

        if run:
            replacements, run_count = self._flush_run(run, mode=mode)
            compacted_entries.extend(replacements)
            compacted_count += run_count

        return compacted_entries, preserved_count, compacted_count

    def _flush_run(
        self,
        run: list[dict[str, Any]],
        *,
        mode: CompactionMode,
    ) -> tuple[list[dict[str, Any]], int]:
        if not run:
            return [], 0
        if mode is CompactionMode.PRESERVE:
            groups = self._group_redundant_entries(run)
            replacements: list[dict[str, Any]] = []
            compacted_count = 0
            for group in groups:
                if len(group) > 1:
                    replacements.append(self._compact_group(group, mode=mode))
                    compacted_count += len(group)
                else:
                    replacements.append(deepcopy(group[0]))
            return replacements, compacted_count
        return [self._compact_group(run, mode=mode)], len(run)

    def _group_redundant_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> list[list[dict[str, Any]]]:
        groups: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        current_key: str | None = None
        for entry in entries:
            key = self._entry_key(entry)
            if current and key != current_key:
                groups.append(current)
                current = []
            current.append(entry)
            current_key = key
        if current:
            groups.append(current)
        return groups

    def _compact_group(
        self,
        entries: list[dict[str, Any]],
        *,
        mode: CompactionMode,
    ) -> dict[str, Any]:
        if len(entries) == 1:
            return self.compact_entry(entries[0], mode=mode)
        key = self._entry_key(entries[0])
        return {
            "type": "compacted_summary",
            "content": self._summarize_group(entries, mode=mode),
            "compaction": {
                "compacted": True,
                "mode": mode.value,
            },
        }

    def _should_compact(self, entry: dict[str, Any], mode: CompactionMode) -> bool:
        score = self._relevance_score(entry)
        if mode is CompactionMode.AGGRESSIVE:
            return score < 0.6
        if mode is CompactionMode.BALANCED:
            return score < 0.35
        return score < 0.2 and self._is_obviously_redundant(entry)

    def _should_preserve(self, entry: dict[str, Any]) -> bool:
        entry_type = str(entry.get("type") or "").strip()
        if entry_type in set(self._config.preserve_event_types):
            return True
        if entry.get("approval_request_id") or entry.get("approval_decision_id"):
            return True
        if entry.get("policy_name"):
            return True
        if entry.get("capability_name") and entry.get("output") is not None:
            return True
        if entry.get("event_type") or str(entry.get("id") or "").startswith("audit_"):
            return True
        return False

    def _is_already_compacted(self, entry: dict[str, Any]) -> bool:
        return str(entry.get("type") or "") == "compacted_summary"

    def _is_obviously_redundant(self, entry: dict[str, Any]) -> bool:
        content = str(entry.get("content") or "").strip().lower()
        return content in {"ok", "okay", "thanks", "thank you", "confirmed", "done"}

    def _relevance_score(self, entry: dict[str, Any]) -> float:
        entry_type = str(entry.get("type") or "message")
        if entry_type in {"decision", "approval_request", "approval_decision", "policy_change", "capability_output"}:
            return 1.0
        if entry.get("event_type"):
            return 1.0
        score = 0.1
        content = str(entry.get("content") or "")
        lowered = content.lower()
        if len(content) > 120:
            score += 0.2
        if any(word in lowered for word in {"decide", "because", "plan", "result", "output"}):
            score += 0.45
        if any(word in lowered for word in {"hello", "thanks", "ok", "sure", "confirmed"}):
            score -= 0.1
        if entry.get("decision") or entry.get("rationale"):
            score += 0.6
        return max(0.0, min(score, 1.0))

    def _summarize_group(
        self,
        entries: list[dict[str, Any]],
        *,
        mode: CompactionMode,
    ) -> str:
        base = self._summarize_entry(entries[0], mode)
        return f"{base}×{len(entries)}"

    def _summarize_entry(self, entry: dict[str, Any], mode: CompactionMode) -> str:
        if entry.get("decision"):
            return f"Decision retained: {entry['decision']}"
        content = str(entry.get("content") or "").strip()
        if not content:
            return "compacted"
        if mode is CompactionMode.AGGRESSIVE:
            return content[:12] or "compacted"
        if mode is CompactionMode.BALANCED:
            return content[:24] or "compacted"
        return content[:24] or "compacted"

    def _entry_key(self, entry: dict[str, Any]) -> str:
        entry_type = str(entry.get("type") or "message")
        content = str(entry.get("content") or entry.get("decision") or "").strip().lower()
        return f"{entry_type}:{content}"

    def _estimate_tokens(self, value: Any) -> int:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return max(0, (len(payload) + 3) // 4)

    def _build_budget_status(
        self,
        *,
        session: dict[str, Any],
        mode: CompactionMode,
    ) -> BudgetStatus:
        token_limit = self._session_token_limit(session)
        threshold = int(token_limit * self._config.trigger_ratio)
        used_tokens = self._estimate_tokens(self._message_entries(session))
        return BudgetStatus(
            token_limit=token_limit,
            threshold_tokens=threshold,
            used_tokens=used_tokens,
            remaining_tokens=token_limit - used_tokens,
            should_compact=used_tokens >= threshold,
            mode=mode,
        )

    def _session_token_limit(self, session: dict[str, Any]) -> int:
        compaction = self._session_compaction_metadata(session)
        override = compaction.get("token_limit")
        if isinstance(override, int) and override > 0:
            return override
        return self._config.token_limit

    def _session_mode(self, session: dict[str, Any]) -> CompactionMode:
        compaction = self._session_compaction_metadata(session)
        default_mode = self._config.default_mode
        raw_mode = compaction.get("mode") or (
            default_mode.value
            if isinstance(default_mode, CompactionMode)
            else str(default_mode)
        )
        return CompactionMode(str(raw_mode))

    def _session_compaction_metadata(self, session: dict[str, Any]) -> dict[str, Any]:
        metadata = session.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        compaction = metadata.get("compaction")
        return deepcopy(compaction) if isinstance(compaction, dict) else {}

    def _message_entries(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        context = session.get("context")
        if not isinstance(context, dict):
            return []
        entries = context.get("messages")
        if not isinstance(entries, list):
            return []
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict):
                normalized.append(deepcopy(entry))
        return normalized

    async def _append_audit(
        self,
        *,
        session: dict[str, Any],
        result: CompactionResult,
        entries: list[dict[str, Any]],
    ) -> None:
        if self._audit is None:
            return
        event = CompactionEvent(
            before_tokens=result.before_tokens,
            after_tokens=result.after_tokens,
            before_size_bytes=len(json.dumps(self._message_entries(session))),
            after_size_bytes=len(json.dumps(entries)),
            preserved_keys=self._preserved_keys(entries),
        )
        await self._audit.append(
            event_type="session_compacted",
            actor=str(session.get("user_id") or "runtime"),
            session_id=session.get("id"),
            status="success",
            metadata=event.model_dump(mode="json"),
        )

    def _preserved_keys(self, entries: list[dict[str, Any]]) -> list[str]:
        keys: list[str] = []
        for entry in entries:
            compaction = entry.get("compaction")
            if isinstance(compaction, dict) and compaction.get("preserved"):
                keys.append(self._entry_key(entry))
        return keys

    async def _load_session(self, session_id: str) -> dict[str, Any]:
        session = await self._store.get_session_state(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return deepcopy(session)

    def _savings_pct(self, before_tokens: int, after_tokens: int) -> float:
        if before_tokens <= 0:
            return 0.0
        savings = ((before_tokens - after_tokens) / before_tokens) * 100
        return round(max(0.0, savings), 2)

    def _require_text(self, value: str | None, field_name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

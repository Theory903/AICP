"""Session state service for runtime-backed execution."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import httpx

from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.auth.models import SessionAuthRecipe, SessionState
from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.audit import AuditService

if TYPE_CHECKING:
    from aicp_runtime.memory.store import MemorySnapshot


class SessionService:
    """Manage stored auth/session artifacts for UI-less execution."""

    def __init__(
        self,
        runtime_store: RuntimeStore,
        audit_service: AuditService | None = None,
    ) -> None:
        self._store = runtime_store
        self._audit = audit_service

    async def create_session(
        self,
        *,
        provider_name: str,
        auth_mode: str,
        cookies: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
        tokens: dict[str, str] | None = None,
        csrf_tokens: dict[str, str] | None = None,
        auth_recipe: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        selected_context: dict[str, Any] | None = None,
        expires_at: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        refreshable: bool = False,
    ) -> dict[str, Any]:
        now = utc_now_rfc3339()
        session = SessionState.model_validate(
            {
                "id": f"sess_{uuid.uuid4().hex[:12]}",
                "provider_name": provider_name,
                "auth_mode": auth_mode,
                "cookies": cookies or [],
                "headers": headers or {},
                "tokens": tokens or {},
                "csrf_tokens": csrf_tokens or {},
                "auth_recipe": auth_recipe,
                "metadata": metadata or {},
                "selected_context": selected_context or {},
                "created_at": now,
                "updated_at": now,
                "expires_at": expires_at,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "refreshable": refreshable,
            }
        )
        payload = session.model_dump(mode="json", exclude_none=True)
        payload = self._with_health(payload)
        await self._store.save_session_state(payload)
        await self._append_audit(
            event_type="session_created",
            actor=str(user_id or "runtime"),
            session_id=session.id,
            status="success",
            metadata={
                "provider_name": session.provider_name,
                "auth_mode": session.auth_mode,
                "tenant_id": session.tenant_id,
            },
        )
        return payload

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = await self._store.get_session_state(
            self._require_text(session_id, "session_id")
        )
        if session is None:
            return None
        if session.get("revoked_at"):
            return None
        return deepcopy(self._with_health(session))

    async def list_sessions(self) -> list[dict[str, Any]]:
        sessions = await self._store.list_session_states()
        active = [session for session in sessions if not session.get("revoked_at")]
        active.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return [deepcopy(self._with_health(session)) for session in active]

    async def revoke_session(self, session_id: str) -> None:
        normalized = self._require_text(session_id, "session_id")
        session = await self._store.get_session_state(normalized)
        if session is None:
            raise ValueError(f"Session not found: {normalized}")
        session["revoked_at"] = utc_now_rfc3339()
        session["updated_at"] = session["revoked_at"]
        await self._store.save_session_state(session)
        await self._append_audit(
            event_type="session_revoked",
            actor=str(session.get("user_id") or "runtime"),
            session_id=normalized,
            status="success",
            metadata={"provider_name": session.get("provider_name")},
        )

    async def refresh_session(self, session_id: str) -> dict[str, Any]:
        normalized = self._require_text(session_id, "session_id")
        session = await self._store.get_session_state(normalized)
        if session is None or session.get("revoked_at"):
            raise ValueError(f"Session not found: {normalized}")

        recipe = self._auth_recipe(session)
        if recipe is None or recipe.kind != "oauth_refresh_token":
            raise ValueError("Session is not refreshable via auth recipe")

        refresh_token_field = recipe.token_field or "refresh_token"
        refresh_token = str((session.get("tokens") or {}).get(refresh_token_field) or "").strip()
        if not refresh_token:
            raise ValueError("Session does not contain a refresh token")
        if not recipe.token_url:
            raise ValueError("Auth recipe is missing token_url")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        if recipe.client_id:
            payload["client_id"] = recipe.client_id
        if recipe.client_secret:
            payload["client_secret"] = recipe.client_secret
        if recipe.scopes:
            payload["scope"] = " ".join(recipe.scopes)
        if recipe.audience:
            payload["audience"] = recipe.audience
        payload.update(recipe.extra_payload)

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.post(recipe.token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()

        access_token = str(token_data.get("access_token") or "").strip()
        if not access_token:
            raise ValueError("Refresh response missing access_token")

        tokens = dict(session.get("tokens") or {})
        tokens["access_token"] = access_token
        new_refresh_token = token_data.get("refresh_token")
        if isinstance(new_refresh_token, str) and new_refresh_token.strip():
            tokens[refresh_token_field] = new_refresh_token.strip()

        session["tokens"] = tokens
        expires_in = token_data.get("expires_in")
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            now_dt = datetime.now(timezone.utc)
            session["expires_at"] = (
                now_dt.replace(microsecond=0)
                .astimezone(timezone.utc)
                .isoformat()
            )
            expiry = now_dt.timestamp() + float(expires_in)
            session["expires_at"] = datetime.fromtimestamp(
                expiry, tz=timezone.utc
            ).replace(microsecond=0).isoformat()

        session["updated_at"] = utc_now_rfc3339()
        session = self._with_health(session)
        await self._store.save_session_state(session)
        await self._append_audit(
            event_type="session_refreshed",
            actor=str(session.get("user_id") or "runtime"),
            session_id=normalized,
            status="success",
            metadata={"provider_name": session.get("provider_name")},
        )
        return deepcopy(session)

    async def mark_used(self, session_id: str) -> dict[str, Any] | None:
        normalized = self._require_text(session_id, "session_id")
        session = await self._store.get_session_state(normalized)
        if session is None or session.get("revoked_at"):
            return None
        session["last_used_at"] = utc_now_rfc3339()
        session["updated_at"] = session["last_used_at"]
        session = self._with_health(session)
        await self._store.save_session_state(session)
        return deepcopy(session)

    async def update_memory(self, session_id: str, snap: "MemorySnapshot") -> None:
        """Persist a MemorySnapshot into the session's metadata."""
        from aicp_runtime.memory.store import MemorySnapshot as _MemorySnapshot  # noqa: F401

        normalized = self._require_text(session_id, "session_id")
        session = await self._store.get_session_state(normalized)
        if session is None:
            raise ValueError(f"Session not found: {normalized}")
        session.setdefault("metadata", {})["memory"] = snap.to_dict()
        session["updated_at"] = utc_now_rfc3339()
        await self._store.save_session_state(session)

    async def get_memory(self, session_id: str) -> "MemorySnapshot | None":
        """Retrieve the persisted MemorySnapshot for a session, or None if not set."""
        from aicp_runtime.memory.store import MemorySnapshot

        normalized = self._require_text(session_id, "session_id")
        session = await self._store.get_session_state(normalized)
        if session is None:
            return None
        raw = session.get("metadata", {}).get("memory")
        if raw is None:
            return None
        return MemorySnapshot.from_dict(raw)

    async def _append_audit(self, event_type: str, actor: str, **fields: Any) -> None:
        if self._audit is None:
            return
        await self._audit.append(event_type=event_type, actor=actor, **fields)

    def _require_text(self, value: str | None, field_name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _with_health(self, session: dict[str, Any]) -> dict[str, Any]:
        enriched = deepcopy(session)
        health_status = self._health_status(enriched)
        enriched["health_status"] = health_status
        enriched["requires_reauth"] = health_status in {"expired", "invalid"}
        return enriched

    def _health_status(self, session: dict[str, Any]) -> str:
        if session.get("revoked_at"):
            return "revoked"

        expires_at = self._parse_timestamp(session.get("expires_at"))
        if expires_at is not None:
            now = datetime.now(timezone.utc)
            if expires_at <= now:
                return "expired"
            if (expires_at - now).total_seconds() <= 300:
                return "stale"

        has_auth_artifacts = bool(session.get("cookies") or session.get("tokens") or session.get("headers"))
        if not has_auth_artifacts and str(session.get("auth_mode") or "").strip().lower() != "anonymous":
            return "invalid"

        return "healthy"

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _auth_recipe(self, session: dict[str, Any]) -> SessionAuthRecipe | None:
        raw_recipe = session.get("auth_recipe")
        if raw_recipe is None:
            return None
        return SessionAuthRecipe.model_validate(raw_recipe)

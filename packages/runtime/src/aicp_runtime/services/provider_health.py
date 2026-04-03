"""Provider health aggregation service."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from aicp.interfaces.capability_provider import CapabilityProvider

from aicp_runtime.persistence.base import RuntimeStore

_AUTH_FAILURE_CODES = {
    "missing_session",
    "needs_reauthentication",
    "provider_session_mismatch",
    "tenant_session_mismatch",
}
_NETWORK_FAILURE_CODES = {
    "timeout",
    "connection_error",
    "dns_failure",
    "tls_error",
}
_WORKFLOW_HEALTH_EVENT_TYPES = {
    "workflow_step_completed",
    "workflow_step_failed",
}


class ProviderHealthService:
    """Aggregate coarse provider health from runtime records."""

    def __init__(
        self,
        runtime_store: RuntimeStore,
        capability_provider: CapabilityProvider,
    ):
        self._store = runtime_store
        self._provider = capability_provider

    async def list_provider_health(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return coarse provider health summaries from recent runtime activity."""
        bounded_limit = max(1, min(limit, 500))
        capability_providers = await self._build_capability_provider_map()
        provider_summaries = self._initialize_provider_summaries(capability_providers)

        signals = [
            *self._execution_record_signals(
                await self._store.list_execution_records(),
                capability_providers,
            ),
            *self._audit_entry_signals(
                await self._store.list_audit_entries(),
                capability_providers,
            ),
        ]
        signals.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)

        for signal in signals:
            provider_key = str(signal.get("provider_key") or "")
            if not provider_key:
                continue
            summary = provider_summaries.setdefault(
                provider_key,
                self._empty_summary(
                    provider_name=str(
                        signal.get("provider_name") or self._provider.provider_name
                    ),
                    provider_type=str(
                        signal.get("provider_type") or self._provider.provider_type
                    ),
                ),
            )
            self._apply_signal(summary, signal)

        results = []
        for summary in provider_summaries.values():
            results.append(deepcopy(self._finalize_summary(summary)))

        results.sort(
            key=lambda item: (
                self._status_rank(str(item.get("health_status") or "unknown")),
                str(item.get("provider_name") or ""),
            )
        )
        return results[:bounded_limit]

    async def _build_capability_provider_map(self) -> dict[str, dict[str, str]]:
        capabilities = await self._provider.discover()
        mapping: dict[str, dict[str, str]] = {}

        for capability in capabilities:
            capability_name = str(getattr(capability, "name", "") or "").strip()
            if not capability_name:
                continue
            provider = getattr(capability, "provider", None)
            provider_name = str(
                getattr(provider, "name", None) or self._provider.provider_name
            ).strip()
            provider_type = str(
                getattr(provider, "type", None) or self._provider.provider_type
            ).strip()
            mapping[capability_name] = {
                "provider_name": provider_name or self._provider.provider_name,
                "provider_type": provider_type or self._provider.provider_type,
            }

        return mapping

    def _initialize_provider_summaries(
        self,
        capability_providers: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, Any]]:
        summaries: dict[str, dict[str, Any]] = {}

        for provider in capability_providers.values():
            provider_key = self._provider_key(
                provider_name=provider["provider_name"],
                provider_type=provider["provider_type"],
            )
            summaries.setdefault(
                provider_key,
                self._empty_summary(
                    provider_name=provider["provider_name"],
                    provider_type=provider["provider_type"],
                ),
            )

        if not summaries:
            default_name = self._provider.provider_name
            default_type = self._provider.provider_type
            summaries[
                self._provider_key(
                    provider_name=default_name, provider_type=default_type
                )
            ] = self._empty_summary(
                provider_name=default_name, provider_type=default_type
            )

        return summaries

    def _execution_record_signals(
        self,
        records: list[dict[str, Any]],
        capability_providers: dict[str, dict[str, str]],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for record in records:
            capability_name = str(record.get("capability_name") or "").strip()
            provider = self._resolve_provider(capability_name, capability_providers)
            raw_result = record.get("result")
            result: dict[str, Any] = raw_result if isinstance(raw_result, dict) else {}
            status = (
                str(record.get("status") or result.get("status") or "").strip().lower()
            )
            error_code = str(result.get("error_code") or "").strip().lower()
            latency_ms = self._latency_ms(record, result)

            signals.append(
                {
                    "provider_key": self._provider_key(**provider),
                    "provider_name": provider["provider_name"],
                    "provider_type": provider["provider_type"],
                    "timestamp": record.get("created_at"),
                    "execution_total": 1,
                    "success_count": 1 if status == "success" else 0,
                    "failure_count": 0 if status == "success" else 1,
                    "auth_failure_count": 1 if error_code in _AUTH_FAILURE_CODES else 0,
                    "network_failure_count": 1
                    if error_code in _NETWORK_FAILURE_CODES
                    else 0,
                    "rate_limit_count": 1 if error_code == "rate_limited" else 0,
                    "latency_ms": latency_ms,
                    "error_code": error_code or None,
                }
            )

        return signals

    def _audit_entry_signals(
        self,
        entries: list[dict[str, Any]],
        capability_providers: dict[str, dict[str, str]],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for entry in entries:
            event_type = str(entry.get("event_type") or "").strip()
            if event_type not in _WORKFLOW_HEALTH_EVENT_TYPES:
                continue

            capability_name = str(entry.get("capability_name") or "").strip()
            if not capability_name:
                continue

            provider = self._resolve_provider(capability_name, capability_providers)
            signals.append(
                {
                    "provider_key": self._provider_key(**provider),
                    "provider_name": provider["provider_name"],
                    "provider_type": provider["provider_type"],
                    "timestamp": entry.get("timestamp"),
                    "execution_total": 0,
                    "success_count": 1
                    if event_type == "workflow_step_completed"
                    else 0,
                    "failure_count": 1 if event_type == "workflow_step_failed" else 0,
                    "auth_failure_count": 0,
                    "network_failure_count": 0,
                    "rate_limit_count": 0,
                    "latency_ms": None,
                    "error_code": None,
                }
            )

        return signals

    def _resolve_provider(
        self,
        capability_name: str,
        capability_providers: dict[str, dict[str, str]],
    ) -> dict[str, str]:
        provider = capability_providers.get(capability_name)
        if provider is not None:
            return provider
        return {
            "provider_name": self._provider.provider_name,
            "provider_type": self._provider.provider_type,
        }

    def _apply_signal(self, summary: dict[str, Any], signal: dict[str, Any]) -> None:
        summary["recent_total"] += 1
        summary["recent_execution_total"] += int(signal.get("execution_total") or 0)
        summary["success_count"] += int(signal.get("success_count") or 0)
        summary["failure_count"] += int(signal.get("failure_count") or 0)
        summary["auth_failure_count"] += int(signal.get("auth_failure_count") or 0)
        summary["network_failure_count"] += int(
            signal.get("network_failure_count") or 0
        )
        summary["rate_limit_count"] += int(signal.get("rate_limit_count") or 0)
        timestamp = signal.get("timestamp")
        if summary["last_activity_at"] is None or str(timestamp or "") > str(
            summary["last_activity_at"] or ""
        ):
            summary["last_activity_at"] = timestamp

        latency_ms = signal.get("latency_ms")
        if isinstance(latency_ms, int | float):
            summary["_latency_total_ms"] += float(latency_ms)
            summary["_latency_sample_count"] += 1

        error_code = str(signal.get("error_code") or "").strip().lower()
        if error_code:
            error_mix = summary.setdefault("_error_code_mix", {})
            error_mix[error_code] = int(error_mix.get(error_code) or 0) + 1
            if summary.get("_last_error_at") is None or str(timestamp or "") >= str(
                summary.get("_last_error_at") or ""
            ):
                summary["_last_error_at"] = timestamp
                summary["last_error_code"] = error_code

    def _empty_summary(
        self, *, provider_name: str, provider_type: str
    ) -> dict[str, Any]:
        return {
            "provider_name": provider_name,
            "provider_type": provider_type,
            "recent_total": 0,
            "recent_execution_total": 0,
            "success_count": 0,
            "failure_count": 0,
            "auth_failure_count": 0,
            "network_failure_count": 0,
            "rate_limit_count": 0,
            "success_rate": 0.0,
            "failure_rate": 0.0,
            "auth_failure_rate": 0.0,
            "network_failure_rate": 0.0,
            "recent_latency_ms": None,
            "recent_error_code_mix": {},
            "last_error_code": None,
            "last_activity_at": None,
            "health_status": "unknown",
            "_latency_total_ms": 0.0,
            "_latency_sample_count": 0,
            "_error_code_mix": {},
            "_last_error_at": None,
        }

    def _provider_key(self, *, provider_name: str, provider_type: str) -> str:
        return f"{provider_name.strip()}::{provider_type.strip()}"

    def _health_status(self, summary: dict[str, Any]) -> str:
        recent_total = int(summary.get("recent_total") or 0)
        recent_execution_total = int(summary.get("recent_execution_total") or 0)
        success_count = int(summary.get("success_count") or 0)
        failure_count = int(summary.get("failure_count") or 0)
        auth_failure_count = int(summary.get("auth_failure_count") or 0)
        network_failure_count = int(summary.get("network_failure_count") or 0)
        rate_limit_count = int(summary.get("rate_limit_count") or 0)
        failure_rate = float(summary.get("failure_rate") or 0.0)

        if recent_total == 0:
            return "unknown"
        if recent_execution_total > 0 and success_count == 0 and failure_count > 0:
            return "unhealthy"
        if recent_execution_total > 0 and failure_rate >= 0.6:
            return "unhealthy"
        if success_count == 0 and failure_count > 0:
            return "unhealthy"
        if (
            auth_failure_count > 0
            or network_failure_count > 0
            or rate_limit_count > 0
            or failure_count > success_count
        ):
            return "degraded"
        if failure_count > 0:
            return "degraded"
        return "healthy"

    def _latency_ms(
        self, record: dict[str, Any], result: dict[str, Any]
    ) -> float | None:
        """Extract a latency estimate from persisted execution data."""
        for candidate in (
            record.get("execution_time_ms"),
            result.get("execution_time_ms"),
        ):
            if isinstance(candidate, int | float):
                return float(candidate)
        return None

    def _finalize_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        """Compute additive derived metrics and strip internal fields."""
        execution_total = int(summary.get("recent_execution_total") or 0)
        latency_samples = int(summary.get("_latency_sample_count") or 0)
        latency_total = float(summary.get("_latency_total_ms") or 0.0)
        error_mix = summary.get("_error_code_mix") or {}

        if execution_total > 0:
            summary["success_rate"] = round(
                int(summary.get("success_count") or 0) / execution_total,
                4,
            )
            summary["failure_rate"] = round(
                int(summary.get("failure_count") or 0) / execution_total,
                4,
            )
            summary["auth_failure_rate"] = round(
                int(summary.get("auth_failure_count") or 0) / execution_total,
                4,
            )
            summary["network_failure_rate"] = round(
                int(summary.get("network_failure_count") or 0) / execution_total,
                4,
            )
        if latency_samples > 0:
            summary["recent_latency_ms"] = round(latency_total / latency_samples, 2)

        summary["recent_error_code_mix"] = {
            key: int(error_mix[key]) for key in sorted(error_mix)
        }
        summary["health_status"] = self._health_status(summary)

        for key in (
            "_latency_total_ms",
            "_latency_sample_count",
            "_error_code_mix",
            "_last_error_at",
        ):
            summary.pop(key, None)
        return summary

    def _status_rank(self, status: str) -> int:
        order = {
            "unhealthy": 0,
            "degraded": 1,
            "healthy": 2,
            "unknown": 3,
        }
        return order.get(status, 4)

"""AICP Risk Inference Engine.

Auto-classifies capabilities by risk level based on:
- HTTP method
- Capability name patterns
- Capability kind

Risk levels map to default policy effects, so developers
get sensible governance out of the box without manual config.
"""

from __future__ import annotations

from enum import Enum

from aicp.capability import CapabilityKind


class RiskLevel(str, Enum):
    """Risk classification for capabilities."""

    LOW = "low"  # Safe queries, reads
    MEDIUM = "medium"  # Standard mutations
    HIGH = "high"  # Financial, sensitive operations
    CRITICAL = "critical"  # Bulk destructive, irreversible


# Patterns that indicate higher risk (checked against capability name)
_CRITICAL_PATTERNS = (
    "delete_all",
    "purge",
    "drop",
    "truncate",
    "destroy",
    "wipe",
    "reset_all",
    "clear_all",
    "revoke_all",
    "bulk_delete",
    "mass_delete",
)

_HIGH_PATTERNS = (
    "transfer",
    "payment",
    "refund",
    "charge",
    "withdraw",
    "payout",
    "invoice",
    "billing",
    "subscription",
    "escalate",
    "revoke",
    "approve",
    "reject",
    "disable",
    "terminate",
    "credential",
    "token",
    "secret",
    "password",
)

_SAFE_PATTERNS = (
    "list",
    "get",
    "search",
    "find",
    "count",
    "check",
    "ping",
    "health",
    "status",
    "version",
    "describe",
    "preview",
    "validate",
)

_DESTRUCTIVE_KEYWORDS = (
    "delete",
    "remove",
    "purge",
    "drop",
    "destroy",
    "wipe",
    "clear",
    "reset",
    "truncate",
    "revoke",
)

_SENSITIVE_KEYWORDS = (
    "auth",
    "login",
    "password",
    "secret",
    "token",
    "credential",
    "permission",
    "role",
    "admin",
    "billing",
    "payment",
    "refund",
)


def _normalize(value: str | None) -> str:
    """Normalize a string for matching."""
    return (value or "").strip().lower()


def _candidate_names(
    capability_name: str,
    func_name: str | None = None,
) -> list[str]:
    """Build normalized candidate names for matching."""
    normalized_capability = _normalize(capability_name)
    parts = [part for part in normalized_capability.split(".") if part]
    last_part = parts[-1] if parts else normalized_capability

    candidates = [normalized_capability, last_part]
    normalized_func = _normalize(func_name)
    if normalized_func:
        candidates.append(normalized_func)

    # Preserve order, remove duplicates
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    """Check whether text contains any pattern."""
    return any(pattern in text for pattern in patterns)


def _endswith_or_exact(text: str, patterns: tuple[str, ...]) -> bool:
    """Check whether text exactly matches or ends with a safe suffix."""
    return any(text == pattern or text.endswith(pattern) for pattern in patterns)


def infer_risk(
    capability_name: str,
    kind: CapabilityKind | str | None = None,
    http_method: str | None = None,
    func_name: str | None = None,
) -> RiskLevel:
    """Infer risk level for a capability.

    Priority order:
    1. Critical name pattern matching
    2. High-risk name pattern matching
    3. Explicit destructive detection
    4. Safe name pattern matching
    5. HTTP method
    6. Capability kind
    7. Default (LOW)

    Args:
        capability_name: Dot-separated capability name (e.g., "notes.delete")
        kind: Capability kind (query, action, etc.)
        http_method: HTTP method (GET, POST, PUT, DELETE, etc.)
        func_name: Original function name for additional pattern matching

    Returns:
        Inferred RiskLevel
    """
    candidates = _candidate_names(capability_name, func_name)
    method = _normalize(http_method).upper()
    kind_str = kind.value if isinstance(kind, CapabilityKind) else _normalize(kind)

    # 1. Critical patterns first
    for candidate in candidates:
        if _contains_any(candidate, _CRITICAL_PATTERNS):
            return RiskLevel.CRITICAL

    # 2. High-risk patterns
    for candidate in candidates:
        if _contains_any(candidate, _HIGH_PATTERNS):
            return RiskLevel.HIGH

    # 3. Explicit destructive detection
    if is_destructive(capability_name, http_method=http_method, func_name=func_name):
        if method == "DELETE" or kind_str == "batch_action":
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM

    # 4. Safe patterns
    for candidate in candidates:
        if _endswith_or_exact(candidate, _SAFE_PATTERNS):
            return RiskLevel.LOW

    # 5. HTTP method-based inference
    if method == "GET":
        return RiskLevel.LOW
    if method == "DELETE":
        return RiskLevel.HIGH
    if method in {"PUT", "PATCH"}:
        return RiskLevel.MEDIUM
    if method == "POST":
        # POST is not automatically "safe". Humans post all kinds of disasters.
        for candidate in candidates:
            if _contains_any(candidate, _SENSITIVE_KEYWORDS):
                return RiskLevel.HIGH
        return RiskLevel.MEDIUM

    # 6. Kind-based inference
    if kind_str == "query":
        return RiskLevel.LOW
    if kind_str == "batch_action":
        return RiskLevel.HIGH
    if kind_str in {"action", "async_action"}:
        return RiskLevel.MEDIUM
    if kind_str == "workflow":
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def risk_to_default_effect(risk: RiskLevel) -> str:
    """Map risk level to a default policy effect.

    This is the convention-over-configuration layer:
    - low → allow
    - medium → ask
    - high → require_approval
    - critical → deny
    """
    mapping = {
        RiskLevel.LOW: "allow",
        RiskLevel.MEDIUM: "ask",
        RiskLevel.HIGH: "require_approval",
        RiskLevel.CRITICAL: "deny",
    }
    return mapping[risk]


def is_destructive(
    capability_name: str,
    http_method: str | None = None,
    func_name: str | None = None,
) -> bool:
    """Check if a capability is destructive.

    A capability is destructive if it:
    - Uses DELETE method
    - Contains destructive keywords in capability or function name
    """
    method = _normalize(http_method).upper()
    if method == "DELETE":
        return True

    for candidate in _candidate_names(capability_name, func_name):
        if _contains_any(candidate, _DESTRUCTIVE_KEYWORDS):
            return True

    return False

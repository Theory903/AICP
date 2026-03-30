"""AICP Risk Inference Engine.

Auto-classifies capabilities by risk level based on:
- HTTP method
- Capability name patterns
- Capability kind

Risk levels map to default policy effects, so developers
get sensible governance out of the box without manual config.
"""

from enum import Enum

from aicp.capability import CapabilityKind


class RiskLevel(str, Enum):
    """Risk classification for capabilities."""

    LOW = "low"  # Safe queries, reads
    MEDIUM = "medium"  # Standard mutations
    HIGH = "high"  # Financial, sensitive operations
    CRITICAL = "critical"  # Bulk destructive, irreversible


# Patterns that indicate higher risk (checked against capability name)
_CRITICAL_PATTERNS = [
    "delete_all",
    "purge",
    "drop",
    "truncate",
    "destroy",
    "wipe",
    "reset_all",
    "clear_all",
]

_HIGH_PATTERNS = [
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
    "revoke_all",
]

_SAFE_PATTERNS = [
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
]


def infer_risk(
    capability_name: str,
    kind: CapabilityKind | str | None = None,
    http_method: str | None = None,
    func_name: str | None = None,
) -> RiskLevel:
    """Infer risk level for a capability.

    Priority order:
    1. Name pattern matching (most specific)
    2. HTTP method
    3. Capability kind
    4. Default (LOW)

    Args:
        capability_name: Dot-separated capability name (e.g., "notes.delete")
        kind: Capability kind (query, action, etc.)
        http_method: HTTP method (GET, POST, PUT, DELETE, etc.)
        func_name: Original function name for additional pattern matching

    Returns:
        Inferred RiskLevel
    """
    # Normalize for pattern matching
    name_lower = capability_name.lower()
    name_parts = name_lower.split(".")
    last_part = name_parts[-1] if name_parts else name_lower

    # Also check function name if available
    check_names = [name_lower, last_part]
    if func_name:
        check_names.append(func_name.lower())

    # 1. Check critical patterns first
    for name in check_names:
        for pattern in _CRITICAL_PATTERNS:
            if pattern in name:
                return RiskLevel.CRITICAL

    # 2. Check high-risk patterns
    for name in check_names:
        for pattern in _HIGH_PATTERNS:
            if pattern in name:
                return RiskLevel.HIGH

    # 3. Check safe patterns
    for name in check_names:
        for pattern in _SAFE_PATTERNS:
            if name.endswith(pattern) or name == pattern:
                return RiskLevel.LOW

    # 4. HTTP method-based inference
    if http_method:
        method = http_method.upper()
        if method == "GET":
            return RiskLevel.LOW
        if method == "DELETE":
            return RiskLevel.MEDIUM
        if method in ("PUT", "PATCH"):
            return RiskLevel.MEDIUM
        if method == "POST":
            return RiskLevel.LOW  # Creates are generally low risk

    # 5. Kind-based inference
    if kind:
        kind_str = kind.value if isinstance(kind, CapabilityKind) else kind
        if kind_str == "query":
            return RiskLevel.LOW
        if kind_str in ("action", "async_action"):
            return RiskLevel.LOW
        if kind_str == "batch_action":
            return RiskLevel.MEDIUM

    return RiskLevel.LOW


def risk_to_default_effect(risk: RiskLevel) -> str:
    """Map risk level to a default policy effect.

    This is the convention-over-configuration layer:
    - low → allow (autonomous execution)
    - medium → ask (require confirmation)
    - high → require_approval (HITL)
    - critical → deny (blocked by default)
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
    - Name contains delete, remove, purge, drop, destroy, wipe, clear, reset
    """
    destructive_keywords = [
        "delete",
        "remove",
        "purge",
        "drop",
        "destroy",
        "wipe",
        "clear",
        "reset",
        "truncate",
    ]

    name_lower = capability_name.lower()
    check_names = [name_lower]
    if func_name:
        check_names.append(func_name.lower())

    for name in check_names:
        for keyword in destructive_keywords:
            if keyword in name:
                return True

    if http_method and http_method.upper() == "DELETE":
        return True

    return False

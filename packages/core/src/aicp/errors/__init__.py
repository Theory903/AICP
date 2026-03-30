"""AICP error definitions."""

from __future__ import annotations

from typing import Any


class AicpError(Exception):
    """Base exception for all AICP errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "unknown",
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details
        self.cause = cause
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert the error to a serializable dictionary."""
        data: dict[str, Any] = {
            "error": self.message,
            "code": self.code,
        }
        if self.details is not None:
            data["details"] = self.details
        if self.cause is not None:
            data["cause"] = str(self.cause)
        return data

    def __str__(self) -> str:
        return self.message


class ValidationError(AicpError):
    """Raised when validation fails."""

    def __init__(
        self,
        field: str,
        message: str,
        *,
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.field = field
        super().__init__(
            f"{field}: {message}",
            code="validation_error",
            details=details,
            cause=cause,
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["field"] = self.field
        return data


class DiscoveryError(AicpError):
    """Raised when capability discovery fails."""

    def __init__(
        self,
        message: str,
        *,
        source_name: str | None = None,
        source_type: str | None = None,
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.source_name = source_name
        self.source_type = source_type

        prefix_parts: list[str] = []
        if source_type:
            prefix_parts.append(source_type)
        if source_name:
            prefix_parts.append(source_name)

        prefix = f"[{'/'.join(prefix_parts)}] " if prefix_parts else ""
        super().__init__(
            f"{prefix}{message}",
            code="discovery_error",
            details=details,
            cause=cause,
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        if self.source_name is not None:
            data["source_name"] = self.source_name
        if self.source_type is not None:
            data["source_type"] = self.source_type
        return data


class ExecutionError(AicpError):
    """Raised when capability execution fails."""

    def __init__(
        self,
        message: str,
        *,
        status: str = "failed",
        capability_name: str | None = None,
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.status = status
        self.capability_name = capability_name
        super().__init__(
            message,
            code="execution_error",
            details=details,
            cause=cause,
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["status"] = self.status
        if self.capability_name is not None:
            data["capability_name"] = self.capability_name
        return data


class PolicyError(AicpError):
    """Raised when policy evaluation fails."""

    def __init__(
        self,
        message: str,
        *,
        requires_confirmation: bool = False,
        policy_name: str | None = None,
        details: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.requires_confirmation = requires_confirmation
        self.policy_name = policy_name
        super().__init__(
            message,
            code="policy_error",
            details=details,
            cause=cause,
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["requires_confirmation"] = self.requires_confirmation
        if self.policy_name is not None:
            data["policy_name"] = self.policy_name
        return data
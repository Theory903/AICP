"""AICP error definitions."""


class AicpError(Exception):
    """Base exception for all AICP errors."""

    def __init__(self, message: str, code: str = "unknown"):
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(AicpError):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}", code="validation_error")


class DiscoveryError(AicpError):
    """Raised when capability discovery fails."""

    def __init__(self, message: str):
        super().__init__(message, code="discovery_error")


class ExecutionError(AicpError):
    """Raised when capability execution fails."""

    def __init__(self, message: str, status: str = "failed"):
        self.status = status
        super().__init__(message, code="execution_error")


class PolicyError(AicpError):
    """Raised when policy evaluation fails."""

    def __init__(self, message: str, requires_confirmation: bool = False):
        self.requires_confirmation = requires_confirmation
        super().__init__(message, code="policy_error")

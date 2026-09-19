"""
Domain exceptions for DevForge Self-Healing and Automated Remediation.
"""

class RemediationError(Exception):
    """Base exception for all remediation errors."""
    pass


class PolicyNotFoundError(RemediationError):
    """Raised when no matching or active policy is found for an event."""
    pass


class RemediationCooldownError(RemediationError):
    """Raised when an application is in cooldown and cannot be remediated yet."""
    def __init__(self, message: str, remaining_seconds: int = 0):
        super().__init__(message)
        self.remaining_seconds = remaining_seconds


class MaxAttemptsExceededError(RemediationError):
    """Raised when remediation has hit the maximum allowed attempts (loop protection)."""
    def __init__(self, message: str, attempts: int = 0, max_attempts: int = 3):
        super().__init__(message)
        self.attempts = attempts
        self.max_attempts = max_attempts


class ActionExecutionError(RemediationError):
    """Raised when executing an allowlisted remediation action fails."""
    pass


class HealthVerificationError(RemediationError):
    """Raised when post-remediation health verification fails to confirm recovery."""
    pass


class ApprovalRequiredError(RemediationError):
    """Raised when an action requires explicit operator approval before execution."""
    pass


class ConcurrencyConflictError(RemediationError):
    """Raised when another remediation action is concurrently executing on the same application."""
    pass

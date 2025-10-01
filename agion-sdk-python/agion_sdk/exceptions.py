"""Exceptions for Agion SDK."""


class AgionSDKError(Exception):
    """Base exception for all Agion SDK errors."""
    pass


class PolicyError(AgionSDKError):
    """Base exception for policy-related errors."""
    pass


class PolicyViolationError(PolicyError):
    """Raised when a policy is violated and enforcement is HARD or CRITICAL."""

    def __init__(self, message: str, policy_id: str = None, decision: str = None):
        super().__init__(message)
        self.policy_id = policy_id
        self.decision = decision


class PolicyEvaluationError(PolicyError):
    """Raised when policy evaluation fails."""
    pass


class PolicySyncError(PolicyError):
    """Raised when policy synchronization fails."""
    pass


class EventError(AgionSDKError):
    """Base exception for event-related errors."""
    pass


class EventPublishError(EventError):
    """Raised when event publishing fails."""
    pass


class ConfigurationError(AgionSDKError):
    """Raised when SDK configuration is invalid."""
    pass


class ConnectionError(AgionSDKError):
    """Raised when connection to backend services fails."""
    pass


class InitializationError(AgionSDKError):
    """Raised when SDK initialization fails."""
    pass


class AuthenticationError(AgionSDKError):
    """Raised when authentication/authorization fails."""
    pass


class ResourceNotFoundError(AgionSDKError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}")
        self.resource_type = resource_type
        self.resource_id = resource_id


class TimeoutError(AgionSDKError):
    """Raised when an operation times out."""
    pass


class ValidationError(AgionSDKError):
    """Raised when data validation fails."""
    pass

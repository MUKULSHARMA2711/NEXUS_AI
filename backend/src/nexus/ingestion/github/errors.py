"""Provider-independent error taxonomy for the GitHub connector."""


class ConnectorError(Exception):
    """Base exception for all connector operations.

    :param message: Human-readable error description (must NOT contain sensitive tokens).
    :param retryable: Boolean indicating if the operation may be retried.
    """

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(message={self.message!r}, retryable={self.retryable})>"


class AuthenticationError(ConnectorError):
    """Raised on HTTP 401 Unauthorized or invalid token."""

    def __init__(self, message: str = "GitHub API authentication failed") -> None:
        super().__init__(message, retryable=False)


class NotFoundError(ConnectorError):
    """Raised on HTTP 404 Not Found."""

    def __init__(self, message: str = "GitHub resource not found") -> None:
        super().__init__(message, retryable=False)


class RateLimitedError(ConnectorError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        retry_at: float | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, retryable=True)
        self.retry_at = retry_at
        self.retry_after = retry_after


class TransientError(ConnectorError):
    """Raised on 5xx server errors or transient network failures."""

    def __init__(self, message: str = "GitHub API transient error") -> None:
        super().__init__(message, retryable=True)


class ProviderClientError(ConnectorError):
    """Raised on other 4xx client errors (e.g., 400 Bad Request, 422 Unprocessable)."""

    def __init__(self, message: str = "GitHub API client error") -> None:
        super().__init__(message, retryable=False)

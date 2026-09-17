"""GitHub connector module for NEXUS engineering data ingestion."""

from nexus.ingestion.github.client import GitHubClient
from nexus.ingestion.github.errors import (
    AuthenticationError,
    ConnectorError,
    NotFoundError,
    ProviderClientError,
    RateLimitedError,
    TransientError,
)

__all__ = [
    "AuthenticationError",
    "ConnectorError",
    "GitHubClient",
    "NotFoundError",
    "ProviderClientError",
    "RateLimitedError",
    "TransientError",
]

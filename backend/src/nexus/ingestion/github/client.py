"""Synchronous HTTP client for interacting with the GitHub REST API v3."""

from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr

from nexus.core.config import get_settings
from nexus.ingestion.github.errors import (
    AuthenticationError,
    NotFoundError,
    ProviderClientError,
    TransientError,
)


class GitHubClient:
    """Synchronous HTTP client for GitHub REST API v3 operations.

    Utilizes `httpx.Client` for synchronous HTTP requests, matching the NEXUS
    synchronous persistence layer.
    """

    def __init__(
        self,
        token: SecretStr | None = None,
        api_url: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self._token = token if token is not None else settings.github_token
        self._api_url = (
            api_url if api_url is not None else settings.github_api_url
        ).rstrip("/")

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "NEXUS-AI-Platform",
        }
        if self._token is not None and self._token.get_secret_value():
            headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"

        self._client = httpx.Client(
            base_url=self._api_url,
            headers=headers,
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        """Send a GET request to a GitHub API endpoint.

        :param endpoint: Relative or full API path (e.g. '/repos/owner/repo')
        :param params: Optional query parameters
        :return: Tuple of (parsed JSON payload, response headers dictionary)
        """
        try:
            response = self._client.get(endpoint, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientError(
                f"Network failure during GitHub API request: {type(exc).__name__}"
            ) from exc
        except Exception as exc:
            raise TransientError(f"Unexpected connection failure: {exc}") from exc

        status_code = response.status_code
        if 200 <= status_code < 300:
            try:
                payload = response.json()
            except Exception as exc:
                raise ProviderClientError(
                    f"Failed to parse JSON response from GitHub API: {exc}"
                ) from exc
            headers_dict = dict(response.headers)
            return payload, headers_dict

        if status_code == 401:
            raise AuthenticationError("GitHub API returned 401 Unauthorized")
        if status_code == 404:
            raise NotFoundError(
                f"GitHub API returned 404 Not Found for endpoint: {endpoint}"
            )
        if status_code >= 500:
            raise TransientError(f"GitHub API returned server error: {status_code}")

        raise ProviderClientError(f"GitHub API returned client error: {status_code}")

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        token_status = "set" if self._token is not None else "unset"
        return f"<GitHubClient(api_url={self._api_url!r}, token={token_status})>"

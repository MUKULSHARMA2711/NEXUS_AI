"""Synchronous HTTP client for interacting with the GitHub REST API v3 with pagination, rate limiting, and retries."""

import random
import time
from collections.abc import Callable, Generator
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import SecretStr

from nexus.core.config import get_settings
from nexus.ingestion.github.errors import (
    AuthenticationError,
    NotFoundError,
    ProviderClientError,
    RateLimitedError,
    TransientError,
)


def parse_link_header(link_header: str | None) -> dict[str, str]:
    """Parse RFC 5988 Link header into a dictionary mapping rel to target URL.

    Example:
      '<https://api.github.com/resource?page=2>; rel="next"' -> {'next': 'https://api.github.com/resource?page=2'}
    """
    if not link_header:
        return {}
    links: dict[str, str] = {}
    for part in link_header.split(","):
        sections = part.strip().split(";")
        if len(sections) < 2:
            continue
        url = sections[0].strip()
        if url.startswith("<") and url.endswith(">"):
            url = url[1:-1]
        for param in sections[1:]:
            param = param.strip()
            if param.startswith("rel="):
                rel = param[4:].strip('"')
                links[rel] = url
    return links


class GitHubClient:
    """Synchronous HTTP client for GitHub REST API v3 operations.

    Includes automatic RFC 5988 Link header pagination, rate-limit detection,
    and exponential backoff retry handling. Matches NEXUS synchronous persistence layer.
    """

    def __init__(
        self,
        token: SecretStr | None = None,
        api_url: str | None = None,
        max_pages: int | None = None,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        sleep_func: Callable[[float], None] | None = time.sleep,
        random_func: Callable[[float, float], float] | None = random.uniform,
    ) -> None:
        settings = get_settings()
        self._token = token if token is not None else settings.github_token
        self._api_url = (
            api_url if api_url is not None else settings.github_api_url
        ).rstrip("/")
        self._max_pages = (
            max_pages if max_pages is not None else settings.github_sync_max_pages
        )
        self._max_retries = max_retries
        self._retry_backoff_factor = retry_backoff_factor
        self._sleep_func = sleep_func
        self._random_func = random_func if random_func is not None else random.uniform

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

    def _raw_get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        """Execute a single HTTP GET request and translate status codes and rate limits."""
        try:
            response = self._client.get(endpoint, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientError(
                f"Network failure during GitHub API request: {type(exc).__name__}"
            ) from exc
        except Exception as exc:
            raise TransientError(f"Unexpected connection failure: {exc}") from exc

        status_code = response.status_code

        # Rate Limit Detection
        remaining = response.headers.get("x-ratelimit-remaining")
        reset_header = response.headers.get("x-ratelimit-reset")
        retry_after_header = response.headers.get("retry-after")

        retry_at = (
            float(reset_header) if reset_header and reset_header.isdigit() else None
        )

        retry_after: float | None = None
        if retry_after_header:
            try:
                retry_after = max(0.0, float(retry_after_header))
            except (ValueError, TypeError):
                retry_after = None

        if status_code in (403, 429) and (
            retry_after is not None
            or remaining == "0"
            or status_code == 429
            or "rate limit" in response.text.lower()
        ):
            raise RateLimitedError(
                "GitHub API rate limit exceeded",
                retry_at=retry_at,
                retry_after=retry_after,
            )

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

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        """Send a GET request with automatic retry on transient errors and secondary rate limits."""
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return self._raw_get(endpoint, params=params)
            except RateLimitedError as exc:
                last_exc = exc
                if exc.retry_after is not None and attempt < self._max_retries:
                    if self._sleep_func:
                        self._sleep_func(exc.retry_after)
                    continue
                raise
            except TransientError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    if self._sleep_func and self._retry_backoff_factor > 0:
                        base_delay = self._retry_backoff_factor * (2**attempt)
                        jitter = (
                            self._random_func(0, base_delay * 0.25)
                            if self._random_func
                            else 0.0
                        )
                        backoff = base_delay + jitter
                        self._sleep_func(backoff)
                    continue
                raise

        if last_exc:
            raise last_exc
        raise TransientError("GitHub API request failed after maximum retries")

    def get_paged(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_pages: int | None = None,
    ) -> Generator[tuple[list[Any], dict[str, str]], None, None]:
        """Paginates GET requests using RFC 5988 Link headers.

        :param endpoint: Endpoint path or starting URL
        :param params: Query parameters (defaults per_page=100)
        :param max_pages: Page limit (defaults to NEXUS_GITHUB_SYNC_MAX_PAGES)
        :return: Generator yielding (page_items_list, page_response_headers)
        """
        effective_max_pages = max_pages if max_pages is not None else self._max_pages
        current_params = dict(params) if params else {}
        if "per_page" not in current_params:
            current_params["per_page"] = 100

        current_url = endpoint
        page_count = 0

        while current_url and page_count < effective_max_pages:
            payload, headers = self.get(
                current_url, params=current_params if page_count == 0 else None
            )
            page_count += 1

            if not isinstance(payload, list):
                yield [payload], headers
                break

            yield payload, headers

            link_header = headers.get("link") or headers.get("Link")
            links = parse_link_header(link_header)

            if "next" in links and page_count < effective_max_pages:
                current_url = links["next"]
                current_params = None
            else:
                break

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

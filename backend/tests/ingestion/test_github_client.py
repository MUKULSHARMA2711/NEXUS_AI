import httpx
import pytest
from pydantic import SecretStr

from nexus.ingestion.github.client import GitHubClient, parse_link_header
from nexus.ingestion.github.errors import (
    AuthenticationError,
    ConnectorError,
    NotFoundError,
    ProviderClientError,
    RateLimitedError,
    TransientError,
)


def test_parse_link_header():
    header = (
        '<https://api.github.com/repositories/123/commits?page=2>; rel="next", '
        '<https://api.github.com/repositories/123/commits?page=5>; rel="last"'
    )
    links = parse_link_header(header)
    assert links == {
        "next": "https://api.github.com/repositories/123/commits?page=2",
        "last": "https://api.github.com/repositories/123/commits?page=5",
    }


def test_parse_link_header_empty():
    assert parse_link_header(None) == {}
    assert parse_link_header("") == {}


def test_github_client_default_construction():
    client = GitHubClient(token=SecretStr("my-secret-token"))
    assert repr(client) == "<GitHubClient(api_url='https://api.github.com', token=set)>"
    assert "my-secret-token" not in repr(client)
    client.close()


def test_github_client_custom_url_and_token():
    client = GitHubClient(
        token=SecretStr("custom-token-123"),
        api_url="https://github.enterprise.local/api/v3/",
    )
    assert (
        repr(client)
        == "<GitHubClient(api_url='https://github.enterprise.local/api/v3', token=set)>"
    )
    assert "custom-token-123" not in repr(client)
    client.close()


def test_github_client_headers_and_authorization():
    captured_request = None

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"name": "NEXUS_AI"})

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(token=SecretStr("secret-pat-xyz"), transport=transport) as client:
        payload, _headers = client.get("/repos/owner/repo")

    assert payload == {"name": "NEXUS_AI"}
    assert captured_request is not None
    assert captured_request.headers["Authorization"] == "Bearer secret-pat-xyz"
    assert captured_request.headers["Accept"] == "application/vnd.github+json"
    assert captured_request.headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert captured_request.headers["User-Agent"] == "NEXUS-AI-Platform"


def test_github_client_unauthenticated_header():
    captured_request = None

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(token=None, transport=transport) as client:
        client.get("/public-repo")

    assert captured_request is not None
    assert "Authorization" not in captured_request.headers


def test_github_client_401_authentication_error():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json={"message": "Bad credentials"})
    )
    with (
        GitHubClient(
            token=SecretStr("secret-token-val"), transport=transport
        ) as client,
        pytest.raises(AuthenticationError) as exc_info,
    ):
        client.get("/user")

    assert "secret-token-val" not in str(exc_info.value)
    assert not exc_info.value.retryable


def test_github_client_404_not_found_error():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(404, json={"message": "Not Found"})
    )
    with (
        GitHubClient(token=SecretStr("token"), transport=transport) as client,
        pytest.raises(NotFoundError) as exc_info,
    ):
        client.get("/repos/owner/nonexistent")

    assert not exc_info.value.retryable


def test_github_client_4xx_client_error():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(422, json={"message": "Validation Failed"})
    )
    with (
        GitHubClient(token=SecretStr("token"), transport=transport) as client,
        pytest.raises(ProviderClientError) as exc_info,
    ):
        client.get("/repos/owner/repo/issues")

    assert not exc_info.value.retryable


def test_token_secrecy_in_exceptions():
    secret_value = "super-secret-token-phrase-999"
    transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json={"message": "Unauthorized"})
    )

    with GitHubClient(token=SecretStr(secret_value), transport=transport) as client:
        try:
            client.get("/test")
        except ConnectorError as exc:
            err_str = str(exc)
            err_repr = repr(exc)
            assert secret_value not in err_str
            assert secret_value not in err_repr


# --- Rate Limit Detection & Secondary Rate Limit Tests ---


def test_github_client_rate_limit_detection_403():
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": "1700000000",
    }
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            403, json={"message": "API rate limit exceeded"}, headers=headers
        )
    )

    with (
        GitHubClient(
            token=SecretStr("token"), transport=transport, sleep_func=mock_sleep
        ) as client,
        pytest.raises(RateLimitedError) as exc_info,
    ):
        client.get("/repos/owner/repo")

    assert exc_info.value.retryable
    assert exc_info.value.retry_at == 1700000000.0
    assert exc_info.value.retry_after is None
    assert len(sleeps) == 0  # Primary rate limit MUST NOT sleep


def test_github_client_rate_limit_detection_429():
    headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": "1700000500",
    }
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            429, json={"message": "Too Many Requests"}, headers=headers
        )
    )

    with (
        GitHubClient(token=SecretStr("token"), transport=transport) as client,
        pytest.raises(RateLimitedError) as exc_info,
    ):
        client.get("/repos/owner/repo")

    assert exc_info.value.retry_at == 1700000500.0


def test_github_client_rate_limit_429_retry_after_success():
    attempts = 0
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                json={"message": "Too Many Requests"},
                headers={"Retry-After": "3"},
            )
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(
        token=SecretStr("token"),
        max_retries=3,
        transport=transport,
        sleep_func=mock_sleep,
    ) as client:
        payload, _ = client.get("/test")

    assert payload == {"status": "ok"}
    assert attempts == 2
    assert sleeps == [3.0]


def test_github_client_secondary_403_retry_after_bounded_retry():
    attempts = 0
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            403,
            json={"message": "You have triggered an abuse detection mechanism."},
            headers={"Retry-After": "5"},
        )

    transport = httpx.MockTransport(handle_request)
    with (
        GitHubClient(
            token=SecretStr("token"),
            max_retries=2,
            transport=transport,
            sleep_func=mock_sleep,
        ) as client,
        pytest.raises(RateLimitedError) as exc_info,
    ):
        client.get("/test")

    assert exc_info.value.retry_after == 5.0
    assert attempts == 3  # 1 initial + 2 retries
    assert sleeps == [5.0, 5.0]


# --- Retry Handling & Jitter Tests ---


def test_github_client_retry_success_after_transient_failure():
    attempts = 0
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json={"status": "recovered"})

    transport = httpx.MockTransport(handle_request)
    client = GitHubClient(
        token=SecretStr("token"),
        max_retries=3,
        retry_backoff_factor=0.1,
        transport=transport,
        sleep_func=mock_sleep,
        random_func=lambda a, b: 0.0,
    )

    payload, _ = client.get("/test")
    assert payload == {"status": "recovered"}
    assert attempts == 2
    assert len(sleeps) == 1
    assert sleeps[0] == 0.1
    client.close()


def test_github_client_jitter_bounded_range():
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    # Inject mock_random returning maximum jitter bound (b = base_delay * 0.25)
    def mock_random(a: float, b: float) -> float:
        assert a == 0.0
        return b  # Max jitter

    attempts = 0

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            return httpx.Response(500, text="Server Error")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(
        token=SecretStr("token"),
        max_retries=3,
        retry_backoff_factor=1.0,
        transport=transport,
        sleep_func=mock_sleep,
        random_func=mock_random,
    ) as client:
        payload, _ = client.get("/test")

    assert payload == {"ok": True}
    assert attempts == 3
    # Attempt 0: base_delay = 1.0, jitter = 0.25 -> total = 1.25
    # Attempt 1: base_delay = 2.0, jitter = 0.50 -> total = 2.50
    assert sleeps == [1.25, 2.50]


def test_github_client_retry_exhaustion():
    attempts = 0
    sleeps: list[float] = []

    def mock_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handle_request)
    client = GitHubClient(
        token=SecretStr("token"),
        max_retries=2,
        retry_backoff_factor=0.1,
        transport=transport,
        sleep_func=mock_sleep,
        random_func=lambda a, b: 0.0,
    )

    with pytest.raises(TransientError):
        client.get("/test")

    assert attempts == 3  # 1 initial attempt + 2 retries
    assert len(sleeps) == 2
    assert sleeps == [0.1, 0.2]
    client.close()


def test_github_client_non_retryable_fails_immediately():
    attempts = 0

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handle_request)
    client = GitHubClient(
        token=SecretStr("token"),
        max_retries=3,
        transport=transport,
    )

    with pytest.raises(NotFoundError):
        client.get("/test")

    assert attempts == 1  # Fails immediately without retry
    client.close()


# --- Pagination (get_paged) Tests ---


def test_get_paged_single_page():
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}])

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(token=SecretStr("token"), transport=transport) as client:
        pages = list(client.get_paged("/repos/owner/repo/commits"))

    assert len(pages) == 1
    items, _headers = pages[0]
    assert items == [{"id": 1}, {"id": 2}]


def test_get_paged_multi_page():
    urls_requested: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        urls_requested.append(str(request.url))
        if "page=2" in str(request.url):
            return httpx.Response(
                200,
                json=[{"id": 3}, {"id": 4}],
                headers={},
            )
        return httpx.Response(
            200,
            json=[{"id": 1}, {"id": 2}],
            headers={
                "Link": '<https://api.github.com/repos/owner/repo/commits?page=2>; rel="next"'
            },
        )

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(token=SecretStr("token"), transport=transport) as client:
        pages = list(client.get_paged("/repos/owner/repo/commits"))

    assert len(pages) == 2
    assert pages[0][0] == [{"id": 1}, {"id": 2}]
    assert pages[1][0] == [{"id": 3}, {"id": 4}]
    assert len(urls_requested) == 2


def test_get_paged_max_pages_ceiling():
    urls_requested: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        urls_requested.append(str(request.url))
        return httpx.Response(
            200,
            json=[{"id": len(urls_requested)}],
            headers={
                "Link": f'<https://api.github.com/items?page={len(urls_requested) + 1}>; rel="next"'
            },
        )

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(
        token=SecretStr("token"), max_pages=2, transport=transport
    ) as client:
        pages = list(client.get_paged("/items"))

    assert len(pages) == 2  # Stopped at max_pages = 2
    assert len(urls_requested) == 2

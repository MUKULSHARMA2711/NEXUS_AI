import httpx
import pytest
from pydantic import SecretStr

from nexus.ingestion.github.client import GitHubClient
from nexus.ingestion.github.errors import (
    AuthenticationError,
    ConnectorError,
    NotFoundError,
    ProviderClientError,
    TransientError,
)


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


def test_github_client_successful_json_and_headers():
    def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"id": 1, "sha": "abc1234"}],
            headers={"Link": '<https://api.github.com/resource?page=2>; rel="next"'},
        )

    transport = httpx.MockTransport(handle_request)
    with GitHubClient(token=SecretStr("token"), transport=transport) as client:
        payload, headers = client.get("/repos/owner/repo/commits")

    assert payload == [{"id": 1, "sha": "abc1234"}]
    assert headers["link"] == '<https://api.github.com/resource?page=2>; rel="next"'


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


def test_github_client_5xx_transient_error():
    transport = httpx.MockTransport(lambda req: httpx.Response(502, text="Bad Gateway"))
    with (
        GitHubClient(token=SecretStr("token"), transport=transport) as client,
        pytest.raises(TransientError) as exc_info,
    ):
        client.get("/repos/owner/repo")

    assert exc_info.value.retryable


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


def test_github_client_network_timeout_transient_error():
    def handle_request(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(handle_request)
    with (
        GitHubClient(token=SecretStr("token"), transport=transport) as client,
        pytest.raises(TransientError) as exc_info,
    ):
        client.get("/repos/owner/repo")

    assert exc_info.value.retryable


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

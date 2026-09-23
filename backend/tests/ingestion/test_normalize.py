import ast
import copy
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import nexus.ingestion.contracts as contracts_module
import nexus.ingestion.github.normalize as normalize_module
from nexus.ingestion.contracts import (
    NormalizedCommit,
    NormalizedIssue,
    NormalizedPullRequest,
    NormalizedRepository,
)
from nexus.ingestion.github.normalize import (
    NormalizationError,
    is_pull_request,
    normalize_commit,
    normalize_issue,
    normalize_pull_request,
    normalize_repository,
)

REPOSITORY_PAYLOAD: dict[str, Any] = {
    "id": 1296269,
    "node_id": "MDEwOlJlcG9zaXRvcnkxMjk2MjY5",
    "name": "api",
    "full_name": "acme/api",
    "owner": {"login": "acme", "id": 1},
    "private": False,
    "html_url": "https://github.com/acme/api",
    "default_branch": "develop",
}

COMMIT_PAYLOAD: dict[str, Any] = {
    "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
    "html_url": "https://github.com/acme/api/commit/6dcb09b5b57875f334f61aebed695e2e4193db5e",
    "commit": {
        "message": "Fix payment timeout\n\nIncrease pool size.",
        "author": {
            "name": "Jane Developer",
            "email": "jane@example.com",
            "date": "2026-09-15T08:00:00Z",
        },
        "committer": {
            "name": "GitHub",
            "email": "noreply@github.com",
            "date": "2026-09-17T10:30:00Z",
        },
    },
    # GitHub account object; must NOT be used as the commit author.
    "author": {"login": "jane-gh-account", "id": 42},
    "committer": {"login": "web-flow", "id": 19864447},
}

PULL_REQUEST_PAYLOAD: dict[str, Any] = {
    "number": 17,
    "state": "open",
    "title": "Add retry to payment client",
    "body": "Adds bounded retries.",
    "html_url": "https://github.com/acme/api/pull/17",
    "user": {"login": "octocat", "id": 1},
    "head": {"sha": "a" * 40, "ref": "feature/retry"},
    "base": {"sha": "b" * 40, "ref": "main"},
    "created_at": "2026-09-10T09:00:00Z",
    "updated_at": "2026-09-11T09:00:00Z",
    "closed_at": None,
    "merged_at": None,
}

ISSUE_PAYLOAD: dict[str, Any] = {
    "number": 123,
    "state": "open",
    "title": "Payment API latency spike",
    "body": "p99 latency above 2s since Tuesday.",
    "html_url": "https://github.com/acme/api/issues/123",
    "user": {"login": "reporter", "id": 7},
    "assignee": {"login": "oncall-engineer", "id": 8},
    "labels": [{"name": "bug"}],
    "created_at": "2026-09-12T12:00:00Z",
    "updated_at": "2026-09-13T12:00:00Z",
    "closed_at": None,
}


def payload(base: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result.update(overrides)
    return result


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def assert_no_placeholder_strings(model: Any) -> None:
    for name, value in model.model_dump().items():
        if isinstance(value, str):
            assert value.lower() not in {"none", "null", "unknown", ""}, name


# --- Repository -------------------------------------------------------------


def test_normalize_repository_complete_payload():
    repository = normalize_repository(REPOSITORY_PAYLOAD)

    assert repository == NormalizedRepository(
        external_id="1296269",
        name="api",
        full_name="acme/api",
        provider="github",
        url="https://github.com/acme/api",
        default_branch="develop",
    )


def test_normalize_repository_provider_is_always_github():
    repository = normalize_repository(payload(REPOSITORY_PAYLOAD, provider="gitlab"))
    assert repository.provider == "github"


def test_normalize_repository_external_id_is_string_of_github_id():
    repository = normalize_repository(REPOSITORY_PAYLOAD)
    assert repository.external_id == "1296269"
    assert isinstance(repository.external_id, str)


def test_normalize_repository_does_not_invent_default_branch():
    with pytest.raises(NormalizationError, match="missing 'default_branch'"):
        normalize_repository(payload(REPOSITORY_PAYLOAD, default_branch=None))


def test_normalize_repository_missing_full_name():
    data = payload(REPOSITORY_PAYLOAD)
    del data["full_name"]

    with pytest.raises(NormalizationError) as exc_info:
        normalize_repository(data)

    assert str(exc_info.value) == "Repository normalization failed: missing 'full_name'"
    assert exc_info.value.resource == "Repository"
    assert exc_info.value.field == "full_name"


def test_normalize_repository_rejects_boolean_id():
    with pytest.raises(NormalizationError, match="'id'"):
        normalize_repository(payload(REPOSITORY_PAYLOAD, id=True))


# --- Commit -----------------------------------------------------------------


def test_normalize_commit_complete_payload():
    commit = normalize_commit(COMMIT_PAYLOAD)

    assert commit == NormalizedCommit(
        sha="6dcb09b5b57875f334f61aebed695e2e4193db5e",
        message="Fix payment timeout\n\nIncrease pool size.",
        author_name="Jane Developer",
        author_email="jane@example.com",
        committed_at=utc(2026, 9, 17, 10, 30),
        url="https://github.com/acme/api/commit/6dcb09b5b57875f334f61aebed695e2e4193db5e",
    )


def test_normalize_commit_uses_git_author_not_github_user():
    commit = normalize_commit(COMMIT_PAYLOAD)
    assert commit.author_name == "Jane Developer"
    assert commit.author_name != "jane-gh-account"


def test_normalize_commit_uses_committer_date_not_author_date():
    commit = normalize_commit(COMMIT_PAYLOAD)
    assert commit.committed_at == utc(2026, 9, 17, 10, 30)


def test_normalize_commit_without_github_user_object():
    commit = normalize_commit(payload(COMMIT_PAYLOAD, author=None, committer=None))
    assert commit.author_name == "Jane Developer"


def test_normalize_commit_missing_author_name_and_email_are_none():
    data = payload(COMMIT_PAYLOAD)
    data["commit"]["author"] = {"date": "2026-09-15T08:00:00Z"}

    commit = normalize_commit(data)

    assert commit.author_name is None
    assert commit.author_email is None


def test_normalize_commit_missing_committer_date():
    data = payload(COMMIT_PAYLOAD)
    del data["commit"]["committer"]["date"]

    with pytest.raises(NormalizationError) as exc_info:
        normalize_commit(data)

    assert (
        str(exc_info.value)
        == "Commit normalization failed: missing 'commit.committer.date'"
    )
    assert exc_info.value.field == "commit.committer.date"


def test_normalize_commit_missing_git_author_object():
    data = payload(COMMIT_PAYLOAD)
    del data["commit"]["author"]

    with pytest.raises(NormalizationError, match="missing 'commit.author'"):
        normalize_commit(data)


def test_normalize_commit_missing_commit_object():
    data = payload(COMMIT_PAYLOAD)
    del data["commit"]

    with pytest.raises(NormalizationError, match="missing 'commit.author'"):
        normalize_commit(data)


def test_normalize_commit_malformed_nested_structure():
    data = payload(COMMIT_PAYLOAD)
    data["commit"]["author"] = "Jane Developer"

    with pytest.raises(NormalizationError, match="'commit.author' must be an object"):
        normalize_commit(data)


def test_normalize_commit_malformed_intermediate_structure():
    with pytest.raises(NormalizationError, match="'commit' must be an object"):
        normalize_commit(payload(COMMIT_PAYLOAD, commit=["not", "an", "object"]))


def test_normalize_commit_missing_sha():
    data = payload(COMMIT_PAYLOAD)
    del data["sha"]

    with pytest.raises(NormalizationError, match="missing 'sha'"):
        normalize_commit(data)


# --- Pull request -----------------------------------------------------------


def test_normalize_open_pull_request():
    pull_request = normalize_pull_request(PULL_REQUEST_PAYLOAD)

    assert pull_request == NormalizedPullRequest(
        number=17,
        title="Add retry to payment client",
        body="Adds bounded retries.",
        state="open",
        author_name="octocat",
        author_email=None,
        url="https://github.com/acme/api/pull/17",
        head_sha="a" * 40,
        base_sha="b" * 40,
        opened_at=utc(2026, 9, 10, 9),
        provider_updated_at=utc(2026, 9, 11, 9),
        merged_at=None,
        closed_at=None,
    )


def test_normalize_closed_unmerged_pull_request():
    pull_request = normalize_pull_request(
        payload(PULL_REQUEST_PAYLOAD, state="closed", closed_at="2026-09-12T09:00:00Z")
    )

    assert pull_request.state == "closed"
    assert pull_request.closed_at == utc(2026, 9, 12, 9)
    assert pull_request.merged_at is None


def test_normalize_merged_pull_request():
    pull_request = normalize_pull_request(
        payload(
            PULL_REQUEST_PAYLOAD,
            state="closed",
            merged_at="2026-09-12T09:00:00Z",
            closed_at="2026-09-12T09:00:00Z",
        )
    )

    assert pull_request.state == "merged"
    assert pull_request.merged_at == utc(2026, 9, 12, 9)
    assert pull_request.closed_at == utc(2026, 9, 12, 9)


def test_normalize_pull_request_nullable_body():
    pull_request = normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, body=None))
    assert pull_request.body is None
    assert_no_placeholder_strings(pull_request)


def test_normalize_pull_request_author_email_when_explicitly_provided():
    data = payload(PULL_REQUEST_PAYLOAD)
    data["user"]["email"] = "octocat@example.com"

    assert normalize_pull_request(data).author_email == "octocat@example.com"


def test_normalize_pull_request_deleted_user():
    pull_request = normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, user=None))
    assert pull_request.author_name is None
    assert pull_request.author_email is None


def test_normalize_pull_request_rejects_unknown_provider_state():
    with pytest.raises(NormalizationError, match="unexpected state 'draft'"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, state="draft"))


def test_normalize_pull_request_missing_number():
    data = payload(PULL_REQUEST_PAYLOAD)
    del data["number"]

    with pytest.raises(
        NormalizationError, match="Pull request normalization failed: missing 'number'"
    ):
        normalize_pull_request(data)


def test_normalize_pull_request_malformed_head():
    with pytest.raises(NormalizationError, match="'head' must be an object"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, head="a" * 40))


def test_normalize_pull_request_oversized_title():
    with pytest.raises(NormalizationError, match="invalid 'title'"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, title="x" * 513))


# --- Issue ------------------------------------------------------------------


def test_normalize_open_issue():
    issue = normalize_issue(ISSUE_PAYLOAD, "acme/api")

    assert issue == NormalizedIssue(
        key="acme/api#123",
        title="Payment API latency spike",
        body="p99 latency above 2s since Tuesday.",
        state="open",
        issue_type=None,
        author_name="reporter",
        author_email=None,
        assignee_name="oncall-engineer",
        url="https://github.com/acme/api/issues/123",
        opened_at=utc(2026, 9, 12, 12),
        closed_at=None,
        provider_updated_at=utc(2026, 9, 13, 12),
    )


def test_normalize_issue_key_uses_repository_full_name():
    assert normalize_issue(ISSUE_PAYLOAD, "acme/api").key == "acme/api#123"
    assert normalize_issue(ISSUE_PAYLOAD, "other-org/billing").key == (
        "other-org/billing#123"
    )


def test_normalize_issue_type_is_not_inferred_from_labels():
    data = payload(ISSUE_PAYLOAD, labels=[{"name": "bug"}, {"name": "incident"}])
    assert normalize_issue(data, "acme/api").issue_type is None


def test_normalize_closed_issue():
    issue = normalize_issue(
        payload(ISSUE_PAYLOAD, state="closed", closed_at="2026-09-14T12:00:00Z"),
        "acme/api",
    )

    assert issue.state == "closed"
    assert issue.closed_at == utc(2026, 9, 14, 12)


def test_normalize_issue_nullable_body_and_assignee():
    issue = normalize_issue(
        payload(ISSUE_PAYLOAD, body=None, assignee=None), "acme/api"
    )

    assert issue.body is None
    assert issue.assignee_name is None
    assert issue.author_email is None
    assert_no_placeholder_strings(issue)


def test_normalize_issue_rejects_pull_request_item():
    data = payload(
        ISSUE_PAYLOAD,
        pull_request={"url": "https://api.github.com/repos/acme/api/pulls/123"},
    )

    assert is_pull_request(data) is True
    with pytest.raises(NormalizationError, match="pull request"):
        normalize_issue(data, "acme/api")


def test_is_pull_request_false_for_plain_issue():
    assert is_pull_request(ISSUE_PAYLOAD) is False


def test_normalize_issue_rejects_empty_repository_full_name():
    with pytest.raises(NormalizationError, match="repository_full_name"):
        normalize_issue(ISSUE_PAYLOAD, "")


def test_normalize_issue_missing_created_at():
    data = payload(ISSUE_PAYLOAD)
    del data["created_at"]

    with pytest.raises(
        NormalizationError, match="Issue normalization failed: missing 'created_at'"
    ):
        normalize_issue(data, "acme/api")


# --- Timestamps -------------------------------------------------------------


def test_timestamp_with_z_suffix():
    pull_request = normalize_pull_request(
        payload(PULL_REQUEST_PAYLOAD, created_at="2026-09-17T10:30:00Z")
    )
    assert pull_request.opened_at == utc(2026, 9, 17, 10, 30)
    assert pull_request.opened_at.utcoffset() == timedelta(0)


def test_timestamp_with_explicit_offset_is_converted_to_utc():
    pull_request = normalize_pull_request(
        payload(PULL_REQUEST_PAYLOAD, created_at="2026-09-17T10:30:00+05:30")
    )
    assert pull_request.opened_at == utc(2026, 9, 17, 5, 0)
    assert pull_request.opened_at.tzinfo is UTC


def test_all_timestamps_are_timezone_aware_utc():
    data = payload(COMMIT_PAYLOAD)
    data["commit"]["committer"]["date"] = "2026-09-17T10:30:00-07:00"

    committed_at = normalize_commit(data).committed_at

    assert committed_at.tzinfo is UTC
    assert committed_at == utc(2026, 9, 17, 17, 30)


def test_malformed_timestamp_raises():
    with pytest.raises(NormalizationError, match="invalid timestamp for 'created_at'"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, created_at="yesterday"))


def test_naive_timestamp_raises_instead_of_assuming_local_time():
    with pytest.raises(NormalizationError, match="has no timezone offset"):
        normalize_pull_request(
            payload(PULL_REQUEST_PAYLOAD, created_at="2026-09-17T10:30:00")
        )


def test_non_string_timestamp_raises():
    with pytest.raises(NormalizationError, match="'updated_at'"):
        normalize_issue(payload(ISSUE_PAYLOAD, updated_at=1726568400), "acme/api")


def test_malformed_optional_timestamp_is_not_silently_dropped():
    with pytest.raises(NormalizationError, match="'merged_at'"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, merged_at="not-a-date"))


# --- General validation -----------------------------------------------------


@pytest.mark.parametrize(
    "normalizer",
    [
        normalize_repository,
        normalize_commit,
        normalize_pull_request,
        lambda data: normalize_issue(data, "acme/api"),
    ],
)
def test_non_object_payload_raises(normalizer):
    with pytest.raises(NormalizationError, match="payload must be an object"):
        normalizer(["not", "a", "dict"])


def test_wrong_scalar_type_raises():
    with pytest.raises(NormalizationError, match="'title' must be a string"):
        normalize_issue(payload(ISSUE_PAYLOAD, title=123), "acme/api")


def test_boolean_is_not_accepted_as_number():
    with pytest.raises(NormalizationError, match="'number' must be an integer"):
        normalize_pull_request(payload(PULL_REQUEST_PAYLOAD, number=True))


def test_normalization_error_is_not_a_connector_error():
    from nexus.ingestion.github.errors import ConnectorError

    assert not issubclass(NormalizationError, ConnectorError)


def test_input_payload_is_not_mutated():
    data = payload(PULL_REQUEST_PAYLOAD)
    snapshot = copy.deepcopy(data)

    normalize_pull_request(data)

    assert data == snapshot


# --- Contracts --------------------------------------------------------------


def test_contracts_are_frozen():
    repository = normalize_repository(REPOSITORY_PAYLOAD)
    with pytest.raises(ValidationError):
        repository.name = "renamed"


def test_contracts_reject_internal_identifiers():
    with pytest.raises(ValidationError):
        NormalizedCommit(
            sha="abc",
            message="msg",
            committed_at=utc(2026, 9, 17),
            repository_id="00000000-0000-0000-0000-000000000000",
        )


def test_contracts_reject_naive_datetimes():
    naive = datetime(2026, 9, 17)  # noqa: DTZ001 - deliberately naive input
    with pytest.raises(ValidationError):
        NormalizedCommit(sha="abc", message="msg", committed_at=naive)


# --- Purity -----------------------------------------------------------------

FORBIDDEN_IMPORT_PREFIXES = (
    "sqlalchemy",
    "psycopg",
    "httpx",
    "fastapi",
    "nexus.db",
    "nexus.models",
    "nexus.core",
    "nexus.api",
    "nexus.ingestion.github.client",
)


@pytest.mark.parametrize("module", [normalize_module, contracts_module])
def test_normalization_modules_have_no_infrastructure_imports(module):
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    for name in imported:
        assert not name.startswith(FORBIDDEN_IMPORT_PREFIXES), name


def test_normalization_runs_without_network_or_environment(monkeypatch):
    for variable in (
        "NEXUS_GITHUB_TOKEN",
        "NEXUS_DATABASE_URL",
        "NEXUS_GITHUB_API_URL",
    ):
        monkeypatch.delenv(variable, raising=False)

    def no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("normalization attempted network access")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    normalize_repository(REPOSITORY_PAYLOAD)
    normalize_commit(COMMIT_PAYLOAD)
    normalize_pull_request(PULL_REQUEST_PAYLOAD)
    normalize_issue(ISSUE_PAYLOAD, "acme/api")

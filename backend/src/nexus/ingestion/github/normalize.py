"""Pure normalization of GitHub REST API payloads into provider-neutral NEXUS contracts.

Functions in this module perform no network, database, or environment access.
Malformed provider payloads raise NormalizationError, which is deliberately
separate from the connector's ConnectorError taxonomy.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from nexus.ingestion.contracts import (
    NormalizedCommit,
    NormalizedIssue,
    NormalizedPullRequest,
    NormalizedRepository,
)

_REPOSITORY = "Repository"
_COMMIT = "Commit"
_PULL_REQUEST = "Pull request"
_ISSUE = "Issue"


class NormalizationError(Exception):
    """Raised when a provider payload is missing required data or is structurally invalid.

    :param resource: Human-readable resource type (e.g. "Commit").
    :param field: Dotted path of the problematic field (e.g. "commit.committer.date").
    :param problem: Description of the problem, used in the message.
    """

    def __init__(self, resource: str, field: str, problem: str) -> None:
        self.resource = resource
        self.field = field
        self.message = f"{resource} normalization failed: {problem}"
        super().__init__(self.message)


def _ensure_object(payload: Any, resource: str) -> None:
    if not isinstance(payload, dict):
        raise NormalizationError(
            resource, "", f"payload must be an object, got {type(payload).__name__}"
        )


def _lookup(payload: dict[str, Any], path: str, resource: str) -> Any:
    """Walk a dotted path; a null or absent intermediate object yields None."""
    current: Any = payload
    walked: list[str] = []
    for part in path.split("."):
        if current is None:
            return None
        if not isinstance(current, dict):
            raise NormalizationError(
                resource, ".".join(walked), f"'{'.'.join(walked)}' must be an object"
            )
        walked.append(part)
        current = current.get(part)
    return current


def _require(payload: dict[str, Any], path: str, resource: str) -> Any:
    value = _lookup(payload, path, resource)
    if value is None:
        raise NormalizationError(resource, path, f"missing '{path}'")
    return value


def _require_object(payload: dict[str, Any], path: str, resource: str) -> None:
    if not isinstance(_require(payload, path, resource), dict):
        raise NormalizationError(resource, path, f"'{path}' must be an object")


def _require_str(payload: dict[str, Any], path: str, resource: str) -> str:
    value = _require(payload, path, resource)
    if not isinstance(value, str):
        raise NormalizationError(resource, path, f"'{path}' must be a string")
    return value


def _optional_str(payload: dict[str, Any], path: str, resource: str) -> str | None:
    value = _lookup(payload, path, resource)
    if value is not None and not isinstance(value, str):
        raise NormalizationError(resource, path, f"'{path}' must be a string")
    return value


def _require_int(payload: dict[str, Any], path: str, resource: str) -> int:
    value = _require(payload, path, resource)
    if isinstance(value, bool) or not isinstance(value, int):
        raise NormalizationError(resource, path, f"'{path}' must be an integer")
    return value


def _parse_timestamp(value: Any, path: str, resource: str) -> datetime:
    """Parse an ISO-8601 timestamp with an explicit offset into an aware UTC datetime."""
    if not isinstance(value, str):
        raise NormalizationError(
            resource, path, f"'{path}' must be an ISO-8601 timestamp string"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise NormalizationError(
            resource, path, f"invalid timestamp for '{path}'"
        ) from None
    if parsed.utcoffset() is None:
        raise NormalizationError(
            resource, path, f"timestamp for '{path}' has no timezone offset"
        )
    return parsed.astimezone(UTC)


def _require_timestamp(payload: dict[str, Any], path: str, resource: str) -> datetime:
    return _parse_timestamp(_require(payload, path, resource), path, resource)


def _optional_timestamp(
    payload: dict[str, Any], path: str, resource: str
) -> datetime | None:
    value = _lookup(payload, path, resource)
    if value is None:
        return None
    return _parse_timestamp(value, path, resource)


def _build[ContractT: BaseModel](
    contract: type[ContractT], resource: str, **fields: Any
) -> ContractT:
    """Construct a contract, translating schema violations into NormalizationError."""
    try:
        return contract(**fields)
    except ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"])
        raise NormalizationError(
            resource, field, f"invalid '{field}': {error['msg']}"
        ) from exc


def is_pull_request(payload: dict[str, Any]) -> bool:
    """Return True if an item from GitHub's /issues endpoint is actually a pull request."""
    return payload.get("pull_request") is not None


def normalize_repository(payload: dict[str, Any]) -> NormalizedRepository:
    _ensure_object(payload, _REPOSITORY)
    external_id = _require(payload, "id", _REPOSITORY)
    if isinstance(external_id, bool) or not isinstance(external_id, int | str):
        raise NormalizationError(_REPOSITORY, "id", "'id' must be an integer or string")
    return _build(
        NormalizedRepository,
        _REPOSITORY,
        external_id=str(external_id),
        name=_require_str(payload, "name", _REPOSITORY),
        full_name=_require_str(payload, "full_name", _REPOSITORY),
        provider="github",
        url=_optional_str(payload, "html_url", _REPOSITORY),
        default_branch=_require_str(payload, "default_branch", _REPOSITORY),
    )


def normalize_commit(payload: dict[str, Any]) -> NormalizedCommit:
    _ensure_object(payload, _COMMIT)
    # Git metadata (commit.author) is authoritative; the GitHub user object is not.
    _require_object(payload, "commit.author", _COMMIT)
    return _build(
        NormalizedCommit,
        _COMMIT,
        sha=_require_str(payload, "sha", _COMMIT),
        message=_require_str(payload, "commit.message", _COMMIT),
        author_name=_optional_str(payload, "commit.author.name", _COMMIT),
        author_email=_optional_str(payload, "commit.author.email", _COMMIT),
        committed_at=_require_timestamp(payload, "commit.committer.date", _COMMIT),
        url=_optional_str(payload, "html_url", _COMMIT),
    )


def normalize_pull_request(payload: dict[str, Any]) -> NormalizedPullRequest:
    _ensure_object(payload, _PULL_REQUEST)
    provider_state = _require_str(payload, "state", _PULL_REQUEST)
    if provider_state not in ("open", "closed"):
        raise NormalizationError(
            _PULL_REQUEST, "state", f"unexpected state {provider_state!r}"
        )
    merged_at = _optional_timestamp(payload, "merged_at", _PULL_REQUEST)
    state = "merged" if merged_at is not None else provider_state
    return _build(
        NormalizedPullRequest,
        _PULL_REQUEST,
        number=_require_int(payload, "number", _PULL_REQUEST),
        title=_require_str(payload, "title", _PULL_REQUEST),
        body=_optional_str(payload, "body", _PULL_REQUEST),
        state=state,
        author_name=_optional_str(payload, "user.login", _PULL_REQUEST),
        author_email=_optional_str(payload, "user.email", _PULL_REQUEST),
        url=_optional_str(payload, "html_url", _PULL_REQUEST),
        head_sha=_optional_str(payload, "head.sha", _PULL_REQUEST),
        base_sha=_optional_str(payload, "base.sha", _PULL_REQUEST),
        opened_at=_require_timestamp(payload, "created_at", _PULL_REQUEST),
        provider_updated_at=_optional_timestamp(payload, "updated_at", _PULL_REQUEST),
        merged_at=merged_at,
        closed_at=_optional_timestamp(payload, "closed_at", _PULL_REQUEST),
    )


def normalize_issue(
    payload: dict[str, Any], repository_full_name: str
) -> NormalizedIssue:
    _ensure_object(payload, _ISSUE)
    if not isinstance(repository_full_name, str) or not repository_full_name:
        raise NormalizationError(
            _ISSUE,
            "repository_full_name",
            "repository_full_name must be a non-empty string",
        )
    if is_pull_request(payload):
        # Issues and PRs share GitHub's number space, so accepting one here would
        # silently create an issue key that collides with a pull request.
        raise NormalizationError(
            _ISSUE, "pull_request", "payload is a pull request, not an issue"
        )
    state = _require_str(payload, "state", _ISSUE)
    if state not in ("open", "closed"):
        raise NormalizationError(_ISSUE, "state", f"unexpected state {state!r}")
    number = _require_int(payload, "number", _ISSUE)
    return _build(
        NormalizedIssue,
        _ISSUE,
        key=f"{repository_full_name}#{number}",
        title=_require_str(payload, "title", _ISSUE),
        body=_optional_str(payload, "body", _ISSUE),
        state=state,
        issue_type=None,
        author_name=_optional_str(payload, "user.login", _ISSUE),
        author_email=None,
        assignee_name=_optional_str(payload, "assignee.login", _ISSUE),
        url=_optional_str(payload, "html_url", _ISSUE),
        opened_at=_require_timestamp(payload, "created_at", _ISSUE),
        closed_at=_optional_timestamp(payload, "closed_at", _ISSUE),
        provider_updated_at=_optional_timestamp(payload, "updated_at", _ISSUE),
    )

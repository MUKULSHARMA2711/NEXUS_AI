"""Provider-neutral normalized contracts produced by ingestion normalizers.

These are immutable boundary objects between provider normalization and the
ingestion service. They carry provider identity (full_name, sha, number, key)
but never internal database identifiers such as repository_id or workspace_id.

String length limits mirror the domain schema so that oversized provider data
is rejected at the normalization boundary instead of failing at persistence.
"""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class NormalizedRepository(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    external_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=512)
    full_name: str = Field(min_length=1, max_length=512)
    provider: Literal["github"]
    url: str | None = Field(default=None, max_length=1024)
    default_branch: str = Field(min_length=1, max_length=100)


class NormalizedCommit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sha: str = Field(min_length=1, max_length=64)
    message: str
    author_name: str | None = Field(default=None, max_length=255)
    author_email: str | None = Field(default=None, max_length=255)
    committed_at: AwareDatetime
    url: str | None = Field(default=None, max_length=1024)


class NormalizedPullRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=512)
    body: str | None = None
    state: Literal["open", "closed", "merged"]
    author_name: str | None = Field(default=None, max_length=255)
    author_email: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=1024)
    head_sha: str | None = Field(default=None, max_length=64)
    base_sha: str | None = Field(default=None, max_length=64)
    opened_at: AwareDatetime
    provider_updated_at: AwareDatetime | None = None
    merged_at: AwareDatetime | None = None
    closed_at: AwareDatetime | None = None


class NormalizedIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=512)
    body: str | None = None
    state: Literal["open", "closed"]
    issue_type: str | None = Field(default=None, max_length=50)
    author_name: str | None = Field(default=None, max_length=255)
    author_email: str | None = Field(default=None, max_length=255)
    assignee_name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=1024)
    opened_at: AwareDatetime
    closed_at: AwareDatetime | None = None
    provider_updated_at: AwareDatetime | None = None

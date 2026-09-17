"""Domain models for NEXUS.

These model imports are intentionally required to ensure that all entity
declarations are registered with Base.metadata for migration tooling (e.g.,
Alembic autogenerate) and metadata discovery across the application.
"""

from nexus.models.commit import Commit
from nexus.models.issue import Issue
from nexus.models.pull_request import PullRequest
from nexus.models.repository import Repository
from nexus.models.workspace import Workspace

__all__ = ["Commit", "Issue", "PullRequest", "Repository", "Workspace"]

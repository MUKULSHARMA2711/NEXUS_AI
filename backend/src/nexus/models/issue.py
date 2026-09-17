import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexus.db.base import Base

if TYPE_CHECKING:
    from nexus.models.repository import Repository
    from nexus.models.workspace import Workspace


class Issue(Base):
    """Issue entity representing an issue tracker item (e.g., GitHub Issue, Jira ticket)."""

    __tablename__ = "issues"

    __table_args__ = (
        # Workspace-scoped uniqueness for issue key
        UniqueConstraint(
            "workspace_id",
            "key",
            name="uq_issues_workspace_id_key",
        ),
        # Optimized for workspace-scoped chronological lookups
        Index("ix_issues_workspace_id_opened_at", "workspace_id", "opened_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    issue_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )
    author_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    author_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    assignee_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        default=None,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # N -> 1 relationship with Workspace
    workspace: Mapped["Workspace"] = relationship(
        back_populates="issues",
    )

    # N -> 1 relationship with Repository (optional)
    repository: Mapped["Repository | None"] = relationship(
        back_populates="issues",
    )

    def __repr__(self) -> str:
        return (
            f"<Issue(id={self.id}, key={self.key!r}, "
            f"workspace_id={self.workspace_id}, state={self.state!r})>"
        )

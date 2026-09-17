import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class PullRequest(Base):
    """PullRequest entity representing a pull request or merge request in a repository."""

    __tablename__ = "pull_requests"

    __table_args__ = (
        # Repository-scoped uniqueness for PR number
        UniqueConstraint(
            "repository_id",
            "number",
            name="uq_pull_requests_repository_id_number",
        ),
        # Optimized for repository-scoped chronological lookups
        Index("ix_pull_requests_repository_id_opened_at", "repository_id", "opened_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
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
    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        default=None,
    )
    head_sha: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
    )
    base_sha: Mapped[str | None] = mapped_column(
        String(64),
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
    merged_at: Mapped[datetime | None] = mapped_column(
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

    # N -> 1 relationship with Repository
    repository: Mapped["Repository"] = relationship(
        back_populates="pull_requests",
    )

    def __repr__(self) -> str:
        return (
            f"<PullRequest(id={self.id}, number={self.number}, "
            f"repository_id={self.repository_id}, state={self.state!r})>"
        )

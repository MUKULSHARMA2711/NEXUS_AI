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


class Commit(Base):
    """Commit entity representing a Git commit in a repository."""

    __tablename__ = "commits"

    __table_args__ = (
        # Repository-scoped uniqueness for commit SHA
        UniqueConstraint(
            "repository_id",
            "sha",
            name="uq_commits_repository_id_sha",
        ),
        # Optimized for repository-scoped chronological lookups
        Index("ix_commits_repository_id_committed_at", "repository_id", "committed_at"),
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
    sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
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
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(
        String(1024),
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
        back_populates="commits",
    )

    def __repr__(self) -> str:
        return (
            f"<Commit(id={self.id}, sha={self.sha!r}, "
            f"repository_id={self.repository_id})>"
        )

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexus.db.base import Base

if TYPE_CHECKING:
    from nexus.models.commit import Commit
    from nexus.models.workspace import Workspace


class Repository(Base):
    """Repository entity representing an ingested code repository."""

    __tablename__ = "repositories"

    __table_args__ = (
        # Prevent duplicate repositories within the same workspace for a provider
        UniqueConstraint(
            "workspace_id",
            "provider",
            "full_name",
            name="uq_repositories_workspace_provider_full_name",
        ),
        # Workspace-scoped lookups by repository name
        Index("ix_repositories_workspace_id_name", "workspace_id", "name"),
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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="github",
        server_default="github",
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        default=None,
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="main",
        server_default="main",
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
        back_populates="repositories",
    )

    # 1 -> N relationship with Commit
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Repository(id={self.id}, full_name={self.full_name!r}, "
            f"provider={self.provider!r}, workspace_id={self.workspace_id})>"
        )

"""TeamInvite — token-based invitations to join a team."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.team import Team
    from shackles.models.user import User


class TeamInvite(UUIDMixin, TimestampMixin, Base):
    """A token-based invitation to join a team."""

    __tablename__ = "TeamInvite"

    token: Mapped[str] = mapped_column(String(100), unique=True)
    invited_email: Mapped[str | None] = mapped_column(
        "invitedEmail", String(255), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        "expiresAt", DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        "usedAt", DateTime(timezone=True), nullable=True
    )

    # ---- FKs ----
    team_id: Mapped[UUID] = mapped_column(
        "teamId",
        PG_UUID(as_uuid=True),
        ForeignKey("Team.id", ondelete="CASCADE"),
        nullable=False,
    )
    invited_by_user_id: Mapped[UUID] = mapped_column(
        "invitedByUserId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        nullable=False,
    )
    used_by_user_id: Mapped[UUID | None] = mapped_column(
        "usedByUserId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Relationships ----
    team: Mapped["Team"] = relationship(back_populates="invites")
    invited_by_user: Mapped["User"] = relationship(
        foreign_keys=[invited_by_user_id],
        back_populates="team_invites_sent",
    )
    used_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[used_by_user_id],
        back_populates="team_invites_used",
    )

    # ---- Indexes ----
    __table_args__ = (
        Index("TeamInvite_teamId_idx", "teamId"),
        Index("TeamInvite_invitedByUserId_idx", "invitedByUserId"),
        Index("TeamInvite_invitedEmail_idx", "invitedEmail"),
    )

    def __repr__(self) -> str:
        return f"<TeamInvite token={self.token[:8]}... team={self.team_id}>"
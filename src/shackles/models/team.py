"""Team model — teams for team events."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.enums import TeamStatus
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.event import Event
    from shackles.models.event_registration import EventRegistration
    from shackles.models.judge_marking import JudgeMarking
    from shackles.models.paper_submission import PaperSubmission
    from shackles.models.team_invite import TeamInvite
    from shackles.models.team_mark import TeamMark
    from shackles.models.user import User


class Team(UUIDMixin, TimestampMixin, Base):
    """A team created for a team event."""

    __tablename__ = "Team"

    # ---- Identity ----
    name: Mapped[str] = mapped_column(String(200))
    name_normalized: Mapped[str] = mapped_column("nameNormalized", String(200))
    team_code: Mapped[str] = mapped_column("teamCode", String(20))
    join_code: Mapped[str | None] = mapped_column(
        "joinCode", String(20), unique=True, nullable=True
    )
    join_code_expires_at: Mapped[datetime | None] = mapped_column(
        "joinCodeExpiresAt", DateTime(timezone=True), nullable=True
    )

    # ---- State ----
    member_count: Mapped[int] = mapped_column(
        "memberCount", Integer, default=0, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=TeamStatus.OPEN.value,
        nullable=False,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        "lockedAt", DateTime(timezone=True), nullable=True
    )
    locked_by: Mapped[str | None] = mapped_column(
        "lockedBy", String(50), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        "cancelledAt", DateTime(timezone=True), nullable=True
    )

    # ---- Leader snapshots ----
    leader_contact_phone_snapshot: Mapped[str | None] = mapped_column(
        "leaderContactPhoneSnapshot", String(20), nullable=True
    )
    leader_contact_email_snapshot: Mapped[str | None] = mapped_column(
        "leaderContactEmailSnapshot", String(255), nullable=True
    )

    # ---- FKs ----
    event_id: Mapped[UUID] = mapped_column(
        "eventId",
        PG_UUID(as_uuid=True),
        ForeignKey("Event.id", ondelete="CASCADE"),
        nullable=False,
    )
    leader_user_id: Mapped[UUID | None] = mapped_column(
        "leaderUserId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Relationships ----
    event: Mapped["Event"] = relationship(back_populates="teams")
    leader: Mapped["User | None"] = relationship(
        foreign_keys=[leader_user_id],
        back_populates="teams_led",
    )
    members: Mapped[list["EventRegistration"]] = relationship(
        back_populates="team",
    )
    invites: Mapped[list["TeamInvite"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )

    team_marks: Mapped[list["TeamMark"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    judge_markings: Mapped[list["JudgeMarking"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )

    paper_submission: Mapped["PaperSubmission | None"] = relationship(
        back_populates="team",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ---- Constraints & indexes ----
    # Only class-body columns here. Mixin columns indexed in migrations.
    __table_args__ = (
        UniqueConstraint("eventId", "nameNormalized",
                         name="Team_eventId_nameNormalized_key"),
        UniqueConstraint("eventId", "teamCode",
                         name="Team_eventId_teamCode_key"),
        Index("Team_joinCode_idx", "joinCode"),
        Index("Team_eventId_status_idx", "eventId", "status"),
        Index("Team_leaderUserId_idx", "leaderUserId"),
    )

    def __repr__(self) -> str:
        return f"<Team {self.name} event={self.event_id}>"
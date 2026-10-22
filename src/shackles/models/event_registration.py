"""EventRegistration — a user's registration for an event."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from shackles.models.enums import (
    RegistrationSource,
    RegistrationSyncStatus,
    TeamMemberRole,
)
from shackles.models.mixins import TimestampMixin, UUIDMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shackles.models.event import Event
    from shackles.models.team import Team
    from shackles.models.user import User

class EventRegistration(UUIDMixin, TimestampMixin, Base):
    """A user's registration for a specific event."""

    __tablename__ = "EventRegistration"

    # ---- FKs ----
    user_id: Mapped[UUID] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        "eventId",
        PG_UUID(as_uuid=True),
        ForeignKey("Event.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[UUID | None] = mapped_column(
        "teamId",
        PG_UUID(as_uuid=True),
        ForeignKey("Team.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Team snapshot ----
    member_role: Mapped[str | None] = mapped_column(
        "memberRole", String(20), nullable=True
    )
    team_name: Mapped[str | None] = mapped_column(
        "teamName", String(200), nullable=True
    )
    team_size: Mapped[int] = mapped_column(
        "teamSize", Integer, default=1, nullable=False
    )

    # ---- Attendance ----
    attended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attended_at: Mapped[datetime | None] = mapped_column(
        "attendedAt", DateTime(timezone=True), nullable=True
    )

    # ---- Registration metadata ----
    source: Mapped[str] = mapped_column(
        String(20),
        default=RegistrationSource.ONLINE.value,
        nullable=False,
    )
    sync_status: Mapped[str] = mapped_column(
        "syncStatus",
        String(20),
        default=RegistrationSyncStatus.APPLIED.value,
        nullable=False,
    )
    station_id: Mapped[str | None] = mapped_column(
        "stationId", String(100), nullable=True
    )
    client_operation_id: Mapped[str | None] = mapped_column(
        "clientOperationId", String(200), unique=True, nullable=True
    )
    sync_error: Mapped[str | None] = mapped_column(
        "syncError", String(500), nullable=True
    )
    synced_at: Mapped[datetime | None] = mapped_column(
        "syncedAt", DateTime(timezone=True), nullable=True
    )

    # ---- Year (denormalized for quick filtering) ----
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Relationships ----
    user: Mapped["User"] = relationship(back_populates="registrations")
    event: Mapped["Event"] = relationship(back_populates="registrations")
    team: Mapped["Team | None"] = relationship(back_populates="members")

    # ---- Constraints & indexes ----
    # Composite indexes involving mixin columns go in migrations.
    __table_args__ = (
        UniqueConstraint("userId", "eventId",
                         name="EventRegistration_userId_eventId_key"),
    )



    def __repr__(self) -> str:
        return f"<EventRegistration user={self.user_id} event={self.event_id}>"
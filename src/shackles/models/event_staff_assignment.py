"""EventStaffAssignment — links staff users to events."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import UUIDMixin

if TYPE_CHECKING:
    from shackles.models.event import Event
    from shackles.models.user import User


class EventStaffAssignment(UUIDMixin, Base):
    """Assigns a staff member (coordinator or volunteer) to an event."""

    __tablename__ = "EventStaffAssignment"

    staff_role: Mapped[str] = mapped_column("staffRole", String(20), nullable=False)

    # ---- FKs ----
    event_id: Mapped[UUID] = mapped_column(
        "eventId",
        PG_UUID(as_uuid=True),
        ForeignKey("Event.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    event: Mapped["Event"] = relationship(back_populates="staff_assignments")
    user: Mapped["User"] = relationship(back_populates="staff_assignments")

    # ---- Constraints & indexes ----
    __table_args__ = (
        UniqueConstraint("eventId", "userId", "staffRole",
                         name="EventStaffAssignment_eventId_userId_staffRole_key"),
        Index("EventStaffAssignment_eventId_userId_idx", "eventId", "userId"),
    )

    def __repr__(self) -> str:
        return f"<EventStaffAssignment user={self.user_id} event={self.event_id}>"
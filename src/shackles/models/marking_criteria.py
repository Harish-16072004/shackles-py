"""MarkingCriteria — scoring configuration for an event."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.criteria_component import CriteriaComponent
    from shackles.models.event import Event
    from shackles.models.judge_marking import JudgeMarking
    from shackles.models.team_mark import TeamMark


class MarkingCriteria(UUIDMixin, TimestampMixin, Base):
    """Scoring criteria for an event (one-to-one with Event)."""

    __tablename__ = "MarkingCriteria"

    name: Mapped[str] = mapped_column(
        String(255), default="Default Marking Criteria",
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    max_marks: Mapped[int] = mapped_column(
        "maxMarks", Integer, default=100, nullable=False,
    )
    number_of_judges: Mapped[int] = mapped_column(
        "numberOfJudges", Integer, default=3, nullable=False,
    )

    # ---- FK to Event (one-to-one) ----
    event_id: Mapped[UUID] = mapped_column(
        "eventId",
        PG_UUID(as_uuid=True),
        ForeignKey("Event.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ---- Relationships ----
    event: Mapped["Event"] = relationship(back_populates="marking_criteria")
    components: Mapped[list["CriteriaComponent"]] = relationship(
        back_populates="criteria",
        cascade="all, delete-orphan",
        order_by="CriteriaComponent.order",
    )
    team_marks: Mapped[list["TeamMark"]] = relationship(
        back_populates="criteria",
        cascade="all, delete-orphan",
    )
    judge_markings: Mapped[list["JudgeMarking"]] = relationship(
        back_populates="criteria",
        cascade="all, delete-orphan",
    )

    # ---- Indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        Index("MarkingCriteria_eventId_idx", "eventId"),
    )

    def __repr__(self) -> str:
        return f"<MarkingCriteria event={self.event_id} name={self.name}>"
        
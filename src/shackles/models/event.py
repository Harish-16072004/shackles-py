"""Event model — symposium events (technical, non-technical, workshops)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.enums import EventCategory, EventParticipationMode
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.event_registration import EventRegistration
    from shackles.models.event_staff_assignment import EventStaffAssignment
    from shackles.models.marking_criteria import MarkingCriteria
    from shackles.models.paper_submission import PaperSubmission
    from shackles.models.team import Team


class Event(UUIDMixin, TimestampMixin, Base):
    """An event in the symposium."""

    __tablename__ = "Event"

    # ---- Identity ----
    name: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    day_label: Mapped[str | None] = mapped_column(
        "dayLabel", String(20), nullable=True
    )

    # ---- Timing ----
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        "endDate", DateTime(timezone=True), nullable=True
    )
    is_all_day: Mapped[bool] = mapped_column(
        "isAllDay", Boolean, default=False, nullable=False
    )

    # ---- Content ----
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    rules_url: Mapped[str | None] = mapped_column(
        "rulesUrl", String(500), nullable=True
    )
    submission_url: Mapped[str | None] = mapped_column(
        "submissionUrl", String(500), nullable=True
    )
    submission_deadline: Mapped[datetime | None] = mapped_column(
        "submissionDeadline", DateTime(timezone=True), nullable=True
    )
    requires_document_submission: Mapped[bool] = mapped_column(
        "requiresDocumentSubmission", Boolean, default=False, nullable=False
    )

    # ---- Contacts ----
    coordinator_name: Mapped[str | None] = mapped_column(
        "coordinatorName", String(200), nullable=True
    )
    coordinator_phone: Mapped[str | None] = mapped_column(
        "coordinatorPhone", String(20), nullable=True
    )
    trainer_name: Mapped[str | None] = mapped_column(
        "trainerName", String(200), nullable=True
    )
    contact_name: Mapped[str | None] = mapped_column(
        "contactName", String(200), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(
        "contactPhone", String(20), nullable=True
    )

    # ---- Participation ----
    participation_mode: Mapped[str] = mapped_column(
        "participationMode",
        String(20),
        default=EventParticipationMode.INDIVIDUAL.value,
        nullable=False,
    )
    team_min_size: Mapped[int | None] = mapped_column(
        "teamMinSize", Integer, nullable=True
    )
    team_max_size: Mapped[int | None] = mapped_column(
        "teamMaxSize", Integer, nullable=True
    )
    max_teams: Mapped[int | None] = mapped_column(
        "maxTeams", Integer, nullable=True
    )
    max_participants: Mapped[int | None] = mapped_column(
        "maxParticipants", Integer, nullable=True
    )

    # ---- State ----
    is_active: Mapped[bool] = mapped_column(
        "isActive", Boolean, default=True, nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(
        "isArchived", Boolean, default=False, nullable=False
    )
    is_template: Mapped[bool] = mapped_column(
        "isTemplate", Boolean, default=False, nullable=False
    )
    template_source_id: Mapped[str | None] = mapped_column(
        "templateSourceId", String(50), nullable=True
    )

    # ---- Constraints & indexes ----
    __table_args__ = (
        UniqueConstraint("year", "name", name="Event_year_name_key"),
        Index("Event_year_isArchived_isActive_idx",
              "year", "isArchived", "isActive"),
        Index("Event_year_isTemplate_idx", "year", "isTemplate"),
        Index("Event_category_year_idx", "category", "year"),
    )

    # ---- Relationships ----
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    teams: Mapped[list["Team"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    staff_assignments: Mapped[list["EventStaffAssignment"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    marking_criteria: Mapped["MarkingCriteria | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )

    paper_submissions: Mapped[list["PaperSubmission"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Event {self.year} {self.name}>"
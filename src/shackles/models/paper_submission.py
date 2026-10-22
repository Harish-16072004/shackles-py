"""PaperSubmission — abstract + presentation pipeline for paper events."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.enums import PaperSelectionStatus
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.event import Event
    from shackles.models.team import Team


class PaperSubmission(UUIDMixin, TimestampMixin, Base):
    """Tracks the abstract → selection → presentation flow for a team.

    One row per team per event. Created automatically when a team locks
    for an event that has `requiresDocumentSubmission = True`.
    """

    __tablename__ = "PaperSubmission"

    # ---- Phase 1: Abstract ----
    abstract_url: Mapped[str | None] = mapped_column(
        "abstractUrl", String(500), nullable=True,
    )
    abstract_submitted_at: Mapped[datetime | None] = mapped_column(
        "abstractSubmittedAt", DateTime(timezone=True), nullable=True,
    )
    abstract_deadline: Mapped[datetime | None] = mapped_column(
        "abstractDeadline", DateTime(timezone=True), nullable=True,
    )

    # ---- Phase 2: Selection ----
    selection_status: Mapped[str] = mapped_column(
        "selectionStatus", String(20),
        default=PaperSelectionStatus.PENDING.value,
        nullable=False,
    )
    selected_at: Mapped[datetime | None] = mapped_column(
        "selectedAt", DateTime(timezone=True), nullable=True,
    )
    selected_by: Mapped[str | None] = mapped_column(
        "selectedBy", String(100), nullable=True,
    )
    selection_note: Mapped[str | None] = mapped_column(
        "selectionNote", String(1000), nullable=True,
    )

    # ---- Phase 3: Presentation ----
    presentation_url: Mapped[str | None] = mapped_column(
        "presentationUrl", String(500), nullable=True,
    )
    presentation_submitted_at: Mapped[datetime | None] = mapped_column(
        "presentationSubmittedAt", DateTime(timezone=True), nullable=True,
    )
    presentation_deadline: Mapped[datetime | None] = mapped_column(
        "presentationDeadline", DateTime(timezone=True), nullable=True,
    )

    # ---- FKs ----
    team_id: Mapped[UUID] = mapped_column(
        "teamId",
        PG_UUID(as_uuid=True),
        ForeignKey("Team.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    event_id: Mapped[UUID] = mapped_column(
        "eventId",
        PG_UUID(as_uuid=True),
        ForeignKey("Event.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    team: Mapped["Team"] = relationship(back_populates="paper_submission")
    event: Mapped["Event"] = relationship(back_populates="paper_submissions")

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "teamId", "eventId",
            name="PaperSubmission_teamId_eventId_key",
        ),
        Index(
            "PaperSubmission_eventId_selectionStatus_idx",
            "eventId", "selectionStatus",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PaperSubmission team={self.team_id} "
            f"status={self.selection_status}>"
        )
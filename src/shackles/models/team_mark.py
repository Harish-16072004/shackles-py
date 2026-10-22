"""TeamMark — aggregate marks for a team's submission in an event."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.component_mark import ComponentMark
    from shackles.models.marking_criteria import MarkingCriteria
    from shackles.models.team import Team


class TeamMark(UUIDMixin, TimestampMixin, Base):
    """Aggregated marks for a team on one event's marking criteria."""

    __tablename__ = "TeamMark"

    total_marks: Mapped[Decimal] = mapped_column(
        "totalMarks", Numeric(6, 2),
        default=Decimal("0"), nullable=False,
    )
    judge_count: Mapped[int] = mapped_column(
        "judgeCount", Integer, default=0, nullable=False,
    )
    is_submitted: Mapped[bool] = mapped_column(
        "isSubmitted", Boolean, default=False, nullable=False,
    )
    submitted_by_admin: Mapped[bool] = mapped_column(
        "submittedByAdmin", Boolean, default=False, nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        "submittedAt", DateTime(timezone=True), nullable=True,
    )
    submitted_by: Mapped[str | None] = mapped_column(
        "submittedBy", String(100), nullable=True,
    )

    # ---- FKs ----
    team_id: Mapped[UUID] = mapped_column(
        "teamId",
        PG_UUID(as_uuid=True),
        ForeignKey("Team.id", ondelete="CASCADE"),
        nullable=False,
    )
    marking_criteria_id: Mapped[UUID] = mapped_column(
        "markingCriteriaId",
        PG_UUID(as_uuid=True),
        ForeignKey("MarkingCriteria.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    team: Mapped["Team"] = relationship(back_populates="team_marks")
    criteria: Mapped["MarkingCriteria"] = relationship(
        back_populates="team_marks",
    )
    component_marks: Mapped[list["ComponentMark"]] = relationship(
        back_populates="team_mark",
        cascade="all, delete-orphan",
    )

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "teamId", "markingCriteriaId",
            name="TeamMark_teamId_markingCriteriaId_key",
        ),
        Index(
            "TeamMark_markingCriteriaId_isSubmitted_idx",
            "markingCriteriaId", "isSubmitted",
        ),
    )

    def __repr__(self) -> str:
        return f"<TeamMark team={self.team_id} total={self.total_marks}>"
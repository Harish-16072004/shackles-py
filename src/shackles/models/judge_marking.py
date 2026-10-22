"""JudgeMarking — an individual judge's marks for one component of one team."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.criteria_component import CriteriaComponent
    from shackles.models.marking_criteria import MarkingCriteria
    from shackles.models.team import Team
    from shackles.models.user import User


class JudgeMarking(UUIDMixin, TimestampMixin, Base):
    """A single judge's marks for a specific team + component.

    This is the raw data. `ComponentMark.average_marks` is the aggregate.
    """

    __tablename__ = "JudgeMarking"

    marks_awarded: Mapped[Decimal] = mapped_column(
        "marksAwarded", Numeric(6, 2), nullable=False,
    )
    judge_notes: Mapped[str | None] = mapped_column(
        "judgeNotes", String(500), nullable=True,
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
    component_id: Mapped[UUID] = mapped_column(
        "componentId",
        PG_UUID(as_uuid=True),
        ForeignKey("CriteriaComponent.id", ondelete="CASCADE"),
        nullable=False,
    )
    judge_id: Mapped[UUID] = mapped_column(
        "judgeId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    team: Mapped["Team"] = relationship(back_populates="judge_markings")
    criteria: Mapped["MarkingCriteria"] = relationship(
        back_populates="judge_markings",
    )
    component: Mapped["CriteriaComponent"] = relationship(
        back_populates="judge_markings",
    )
    judge: Mapped["User"] = relationship(back_populates="judge_markings")

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "teamId", "markingCriteriaId", "componentId", "judgeId",
            name="JudgeMarking_teamId_markingCriteriaId_componentId_judgeId_key",
        ),
        Index(
            "JudgeMarking_markingCriteriaId_judgeId_idx",
            "markingCriteriaId", "judgeId",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<JudgeMarking team={self.team_id} judge={self.judge_id} "
            f"marks={self.marks_awarded}>"
        )
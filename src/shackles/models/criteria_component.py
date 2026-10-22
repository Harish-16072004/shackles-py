"""CriteriaComponent — a scored component within marking criteria."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
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
    from shackles.models.judge_marking import JudgeMarking
    from shackles.models.marking_criteria import MarkingCriteria


class CriteriaComponent(UUIDMixin, TimestampMixin, Base):
    """A single scored component within marking criteria.

    Example: "Innovation" worth 25% of the total, max 25 marks.
    """

    __tablename__ = "CriteriaComponent"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    weight_percentage: Mapped[Decimal] = mapped_column(
        "weightPercentage", Numeric(5, 2), nullable=False,
    )
    max_marks_for_component: Mapped[int] = mapped_column(
        "maxMarksForComponent", Integer, nullable=False,
    )
    order: Mapped[int] = mapped_column(
        "order", Integer, default=0, nullable=False,
    )

    # ---- FK to MarkingCriteria ----
    marking_criteria_id: Mapped[UUID] = mapped_column(
        "markingCriteriaId",
        PG_UUID(as_uuid=True),
        ForeignKey("MarkingCriteria.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    criteria: Mapped["MarkingCriteria"] = relationship(
        back_populates="components",
    )
    component_marks: Mapped[list["ComponentMark"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
    )
    judge_markings: Mapped[list["JudgeMarking"]] = relationship(
        back_populates="component",
        cascade="all, delete-orphan",
    )

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "markingCriteriaId", "order",
            name="CriteriaComponent_markingCriteriaId_order_key",
        ),
        Index(
            "CriteriaComponent_markingCriteriaId_idx",
            "markingCriteriaId",
        ),
    )

    def __repr__(self) -> str:
        return f"<CriteriaComponent {self.name} criteria={self.marking_criteria_id}>"
"""ComponentMark — per-component aggregate marks for a team."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.criteria_component import CriteriaComponent
    from shackles.models.team_mark import TeamMark


class ComponentMark(UUIDMixin, TimestampMixin, Base):
    """Aggregated marks for one team on one component (across all judges)."""

    __tablename__ = "ComponentMark"

    average_marks: Mapped[Decimal] = mapped_column(
        "averageMarks", Numeric(6, 2),
        default=Decimal("0"), nullable=False,
    )
    judge_count: Mapped[int] = mapped_column(
        "judgeCount", Integer, default=0, nullable=False,
    )

    # ---- FKs ----
    team_mark_id: Mapped[UUID] = mapped_column(
        "teamMarkId",
        PG_UUID(as_uuid=True),
        ForeignKey("TeamMark.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_id: Mapped[UUID] = mapped_column(
        "componentId",
        PG_UUID(as_uuid=True),
        ForeignKey("CriteriaComponent.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ---- Relationships ----
    team_mark: Mapped["TeamMark"] = relationship(
        back_populates="component_marks",
    )
    component: Mapped["CriteriaComponent"] = relationship(
        back_populates="component_marks",
    )

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "teamMarkId", "componentId",
            name="ComponentMark_teamMarkId_componentId_key",
        ),
        Index(
            "ComponentMark_teamMarkId_componentId_idx",
            "teamMarkId", "componentId",
        ),
    )

    def __repr__(self) -> str:
        return f"<ComponentMark team_mark={self.team_mark_id} avg={self.average_marks}>"
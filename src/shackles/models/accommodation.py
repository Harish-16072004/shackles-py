"""Accommodation — accommodation requests from participants."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.user import User


class Accommodation(UUIDMixin, TimestampMixin, Base):
    """A participant's accommodation request."""

    __tablename__ = "Accommodation"

    days: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    # ---- FKs ----
    user_id: Mapped[UUID] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(back_populates="accommodation")

    def __repr__(self) -> str:
        return f"<Accommodation user={self.user_id} days={self.days}>"
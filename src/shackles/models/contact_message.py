"""ContactMessage — messages submitted via the contact form."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import UUIDMixin

if TYPE_CHECKING:
    from shackles.models.user import User


class ContactMessage(UUIDMixin, Base):
    """A message submitted via the public contact form.

    Note: uses only UUIDMixin + a manual createdAt — no updatedAt,
    because the Prisma schema does not track it.
    """

    __tablename__ = "ContactMessage"

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255))
    mobile: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(2000))

    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---- Optional FK to User (message submitter if logged in) ----
    user_id: Mapped[UUID | None] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Relationships ----
    user: Mapped["User | None"] = relationship(
        back_populates="contact_messages",
    )

    def __repr__(self) -> str:
        return f"<ContactMessage from={self.email}>"
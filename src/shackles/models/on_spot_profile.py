"""OnSpotProfile — additional metadata for on-spot registrants."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shackles.models.user import User


class OnSpotProfile(UUIDMixin, TimestampMixin, Base):
    """Extra metadata recorded when someone registers on-spot."""

    __tablename__ = "OnSpotProfile"

    station_id: Mapped[str | None] = mapped_column(
        "stationId", String(100), nullable=True
    )
    device_id: Mapped[str | None] = mapped_column(
        "deviceId", String(100), nullable=True
    )
    referral_source: Mapped[str | None] = mapped_column(
        "referralSource", String(200), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ---- FKs ----
    user_id: Mapped[UUID] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        "createdByUserId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="on_spot_profile",
    )

    # ---- Indexes ----
    __table_args__ = (
        Index("OnSpotProfile_stationId_idx", "stationId"),
    )

    def __repr__(self) -> str:
        return f"<OnSpotProfile user={self.user_id}>"
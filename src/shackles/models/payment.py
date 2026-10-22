"""Payment model — payment records for registrations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.enums import (
    PackageType,
    PaymentCaptureSource,
    PaymentChannel,
    PaymentStatus,
)
from shackles.models.mixins import TimestampMixin, UUIDMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shackles.models.user import User


class Payment(UUIDMixin, TimestampMixin, Base):
    """Payment record — one per user."""

    __tablename__ = "Payment"

    # ---- Amount & reference ----
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_id: Mapped[str] = mapped_column("transactionId", String(100))
    proof_url: Mapped[str] = mapped_column("proofUrl", String(500))
    proof_path: Mapped[str | None] = mapped_column(
        "proofPath", String(500), nullable=True
    )

    # ---- Status & metadata ----
    status: Mapped[str] = mapped_column(
        String(20),
        default=PaymentStatus.PENDING.value,
        nullable=False,
    )
    payment_channel: Mapped[str] = mapped_column(
        "paymentChannel",
        String(20),
        default=PaymentChannel.ONLINE.value,
        nullable=False,
    )
    capture_source: Mapped[str] = mapped_column(
        "captureSource",
        String(20),
        default=PaymentCaptureSource.WEBSITE.value,
        nullable=False,
    )
    package_type: Mapped[str | None] = mapped_column(
        "packageType",
        String(20),
        nullable=True,
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Verification ----
    verification_device_id: Mapped[str | None] = mapped_column(
        "verificationDeviceId", String(100), nullable=True
    )
    verification_note: Mapped[str | None] = mapped_column(
        "verificationNote", String(500), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        "verifiedAt", DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[str | None] = mapped_column(
        "verifiedBy", String(50), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        "rejectedAt", DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        "rejectionReason", String(500), nullable=True
    )

    # ---- FK to User (one-to-one) ----
    user_id: Mapped[UUID] = mapped_column(
        "userId",
        PG_UUID(as_uuid=True),
        ForeignKey("User.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(back_populates="payment")

    # ---- Indexes ----
    # Mixin-column indexes (created_at, updated_at) are added in migrations
    # to avoid SQLAlchemy's resolution-order issues. Only indexes on
    # locally-defined columns go here.
    __table_args__ = ()

    def __repr__(self) -> str:
        return f"<Payment user_id={self.user_id} status={self.status}>"
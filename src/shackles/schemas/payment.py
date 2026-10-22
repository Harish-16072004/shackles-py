"""Payment schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from shackles.models.enums import (
    PackageType,
    PaymentCaptureSource,
    PaymentChannel,
    PaymentStatus,
)
from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class PaymentBase(ApiBase):
    """Shared payment fields."""

    amount: int = Field(ge=0)
    payment_channel: PaymentChannel = PaymentChannel.ONLINE
    package_type: PackageType | None = None
    year: int | None = Field(default=None, ge=2000, le=3000)


class PaymentCreate(PaymentBase, ApiWrite):
    """Payload for creating a payment (registration flow)."""

    transaction_id: str = Field(min_length=1, max_length=100)
    proof_url: str = Field(min_length=1, max_length=500)
    proof_path: str | None = Field(default=None, max_length=500)
    capture_source: PaymentCaptureSource = PaymentCaptureSource.WEBSITE


class PaymentRead(ApiRead):
    """Public payment representation."""

    id: UUID
    user_id: UUID
    amount: int
    transaction_id: str
    proof_url: str
    proof_path: str | None
    status: PaymentStatus
    payment_channel: PaymentChannel
    capture_source: PaymentCaptureSource
    package_type: PackageType | None
    year: int | None
    verified_at: datetime | None
    verified_by: str | None
    rejected_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class PaymentVerify(ApiWrite):
    """Payload for admin approving or rejecting a payment."""

    action: str = Field(pattern="^(APPROVE|REJECT)$")
    verification_note: str | None = Field(default=None, max_length=500)
    rejection_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _require_reason_on_reject(self) -> "PaymentVerify":
        if self.action == "REJECT" and not self.rejection_reason:
            raise ValueError(
                "rejection_reason is required when action is REJECT"
            )
        return self
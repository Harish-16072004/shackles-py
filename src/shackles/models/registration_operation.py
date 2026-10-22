"""RegistrationOperation — log of every scanner operation (audit + replay).

Used for offline-capable scanners: each operation is recorded with a
client-supplied `operationId` so retries can be deduplicated.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shackles.db.base import Base
from shackles.models.enums import (
    RegistrationOperationType,
    RegistrationSyncStatus,
)
from shackles.models.mixins import TimestampMixin, UUIDMixin


class RegistrationOperation(UUIDMixin, TimestampMixin, Base):
    """An audit record of a scanner operation."""

    __tablename__ = "RegistrationOperation"

    operation_id: Mapped[str] = mapped_column(
        "operationId", String(200), unique=True, nullable=False,
    )
    station_id: Mapped[str] = mapped_column(
        "stationId", String(100), nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(
        "operationType", String(30), nullable=False,
    )

    # ---- Actors (denormalized strings — not FKs in Prisma) ----
    actor_user_id: Mapped[str | None] = mapped_column(
        "actorUserId", String(50), nullable=True,
    )
    participant_id: Mapped[str | None] = mapped_column(
        "participantId", String(50), nullable=True,
    )
    team_leader_user_id: Mapped[str | None] = mapped_column(
        "teamLeaderUserId", String(50), nullable=True,
    )

    # ---- Context ----
    event_name: Mapped[str | None] = mapped_column(
        "eventName", String(200), nullable=True,
    )
    team_name: Mapped[str | None] = mapped_column(
        "teamName", String(200), nullable=True,
    )

    # ---- Payload ----
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True,
    )
    payload_hash: Mapped[str | None] = mapped_column(
        "payloadHash", String(128), nullable=True,
    )

    # ---- Result ----
    status: Mapped[str] = mapped_column(
        String(20),
        default=RegistrationSyncStatus.PENDING.value,
        nullable=False,
    )
    conflict_reason: Mapped[str | None] = mapped_column(
        "conflictReason", String(500), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        "errorMessage", String(1000), nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        "processedAt", DateTime(timezone=True), nullable=True,
    )

    # ---- Indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        Index(
            "RegistrationOperation_stationId_createdAt_idx",
            "stationId", "createdAt",
        ),
        Index(
            "RegistrationOperation_status_createdAt_idx",
            "status", "createdAt",
        ),
        Index(
            "RegistrationOperation_participantId_idx",
            "participantId",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RegistrationOperation {self.operation_type} "
            f"station={self.station_id}>"
        )
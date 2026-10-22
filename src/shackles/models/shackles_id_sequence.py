"""ShacklesIdSequence — atomic counter for Shackles ID allocation.

Each (year, registrationType) pair has its own counter row. The allocator
increments `lastIssued` inside a serializable transaction to guarantee
unique IDs even under concurrent verification.
"""

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shackles.db.base import Base
from shackles.models.enums import RegistrationType
from shackles.models.mixins import TimestampMixin, UUIDMixin


class ShacklesIdSequence(UUIDMixin, TimestampMixin, Base):
    """Counter tracking the last-issued sequence number per (year, type)."""

    __tablename__ = "ShacklesIdSequence"

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_type: Mapped[str] = mapped_column(
        "registrationType", String(20),
        default=RegistrationType.GENERAL.value,
        nullable=False,
    )
    last_issued: Mapped[int] = mapped_column(
        "lastIssued", Integer, default=0, nullable=False,
    )

    # ---- Constraints & indexes ----
    # Strings below are DB column names (camelCase).
    __table_args__ = (
        UniqueConstraint(
            "year", "registrationType",
            name="ShacklesIdSequence_year_registrationType_key",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ShacklesIdSequence {self.year}/{self.registration_type} "
            f"last={self.last_issued}>"
        )
"""User model — participants, staff, and admins."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shackles.db.base import Base
from shackles.models.enums import KitStatus, RegistrationType, Role
from shackles.models.mixins import TimestampMixin, UUIDMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shackles.models.accommodation import Accommodation
    from shackles.models.contact_message import ContactMessage
    from shackles.models.event_registration import EventRegistration
    from shackles.models.event_staff_assignment import EventStaffAssignment
    from shackles.models.judge_marking import JudgeMarking
    from shackles.models.on_spot_profile import OnSpotProfile
    from shackles.models.payment import Payment
    from shackles.models.team import Team
    from shackles.models.team_invite import TeamInvite

class User(UUIDMixin, TimestampMixin, Base):
    """A person in the system — applicant, participant, staff, or admin."""

    __tablename__ = "User"

    # ---- Identity ----
    first_name: Mapped[str] = mapped_column("firstName", String(100))
    last_name: Mapped[str] = mapped_column("lastName", String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    password: Mapped[str] = mapped_column(String(255))

    # ---- College info ----
    college_name: Mapped[str] = mapped_column("collegeName", String(255))
    college_loc: Mapped[str] = mapped_column("collegeLoc", String(255))
    department: Mapped[str] = mapped_column(String(100))
    year_of_study: Mapped[str] = mapped_column("yearOfStudy", String(10))
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ---- Role & registration ----
    role: Mapped[str] = mapped_column(
        String(20),
        default=Role.APPLICANT.value,
        nullable=False,
    )
    registration_type: Mapped[str] = mapped_column(
        "registrationType",
        String(20),
        default=RegistrationType.GENERAL.value,
        nullable=False,
    )

    # ---- Shackles-specific identifiers ----
    shackles_id: Mapped[str | None] = mapped_column(
        "shacklesId",
        String(20),
        unique=True,
        nullable=True,
    )
    qr_token: Mapped[str | None] = mapped_column(
        "qrToken",
        String(128),
        unique=True,
        nullable=True,
    )
    qr_image_url: Mapped[str | None] = mapped_column(
        "qrImageUrl",
        String(500),
        nullable=True,
    )
    qr_path: Mapped[str | None] = mapped_column(
        "qrPath",
        String(500),
        nullable=True,
    )
    qr_token_expiry: Mapped[datetime | None] = mapped_column(
        "qrTokenExpiry",
        DateTime(timezone=True),
        nullable=True,
    )
    last_qr_scan: Mapped[datetime | None] = mapped_column(
        "lastQrScan",
        DateTime(timezone=True),
        nullable=True,
    )

    # ---- Kit status ----
    kit_status: Mapped[str] = mapped_column(
        "kitStatus",
        String(20),
        default=KitStatus.PENDING.value,
        nullable=False,
    )
    kit_issued_at: Mapped[datetime | None] = mapped_column(
        "kitIssuedAt",
        DateTime(timezone=True),
        nullable=True,
    )
    kit_issued_by: Mapped[str | None] = mapped_column(
        "kitIssuedBy",
        String(100),
        nullable=True,
    )

    # ---- Password reset ----
    verification_token: Mapped[str | None] = mapped_column(
        "verificationToken",
        String(128),
        unique=True,
        nullable=True,
    )
    reset_token: Mapped[str | None] = mapped_column(
        "resetToken",
        String(128),
        unique=True,
        nullable=True,
    )
    reset_token_expiry: Mapped[datetime | None] = mapped_column(
        "resetTokenExpiry",
        DateTime(timezone=True),
        nullable=True,
    )

    # ---- Indexes ----
    # Defined manually in migrations to avoid SQLAlchemy's resolution-order
    # issues with mixin columns.

    # ---- Relationships ----
    payment: Mapped["Payment | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    teams_led: Mapped[list["Team"]] = relationship(
        foreign_keys="[Team.leader_user_id]",
        back_populates="leader",
    )
    team_invites_sent: Mapped[list["TeamInvite"]] = relationship(
        foreign_keys="[TeamInvite.invited_by_user_id]",
        back_populates="invited_by_user",
    )
    team_invites_used: Mapped[list["TeamInvite"]] = relationship(
        foreign_keys="[TeamInvite.used_by_user_id]",
        back_populates="used_by_user",
    )
    staff_assignments: Mapped[list["EventStaffAssignment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    on_spot_profile: Mapped["OnSpotProfile | None"] = relationship(
        foreign_keys="[OnSpotProfile.user_id]",
        back_populates="user",
        uselist=False,
    )
    accommodation: Mapped["Accommodation | None"] = relationship(
        back_populates="user",
        uselist=False,
    )

    judge_markings: Mapped[list["JudgeMarking"]] = relationship(
        back_populates="judge",
        cascade="all, delete-orphan",
    )
    contact_messages: Mapped[list["ContactMessage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    def __repr__(self) -> str:
        return f"<User {self.email}>"
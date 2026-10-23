"""Shared pytest fixtures for Shackles Symposium unit and API tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from shackles.models.enums import (
    EventCategory,
    EventParticipationMode,
    KitStatus,
    PackageType,
    PaymentCaptureSource,
    PaymentChannel,
    PaymentStatus,
    RegistrationType,
    Role,
    TeamStatus,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return a mocked SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    return session


@pytest.fixture
def sample_user() -> SimpleNamespace:
    """Return an ORM-like participant user instance."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        first_name="Priya",
        last_name="raman",
        email="priya@example.com",
        phone="9876543210",
        password="$2b$12$abcdefghijklmnopqrstuv1234567890123456789012345678901",
        college_name="Anna University",
        college_loc="Chennai",
        department="CSE",
        year_of_study="III",
        gender="FEMALE",
        role=Role.PARTICIPANT.value,
        registration_type=RegistrationType.COMBO.value,
        shackles_id="SH26C001",
        qr_token="a" * 64,
        qr_image_url="http://localhost:8000/static/qr-codes/2026/sample.png",
        qr_path="qr-codes/2026/sample.png",
        qr_token_expiry=now + timedelta(days=30),
        kit_status=KitStatus.PENDING.value,
        kit_issued_at=None,
        kit_issued_by=None,
        reset_token=None,
        reset_token_expiry=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_admin() -> SimpleNamespace:
    """Return an ORM-like admin user instance."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        first_name="Harish",
        last_name="Admin",
        email="admin@shackles.local",
        phone="9123456789",
        password="$2b$12$abcdefghijklmnopqrstuv1234567890123456789012345678901",
        college_name="ACGCET",
        college_loc="Karaikudi",
        department="Mechanical",
        year_of_study="IV",
        gender="MALE",
        role=Role.ADMIN.value,
        registration_type=RegistrationType.COMBO.value,
        shackles_id="SH26C000",
        qr_token="b" * 64,
        qr_image_url=None,
        qr_path=None,
        qr_token_expiry=now + timedelta(days=30),
        kit_status=KitStatus.PENDING.value,
        kit_issued_at=None,
        kit_issued_by=None,
        reset_token=None,
        reset_token_expiry=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_payment(sample_user: SimpleNamespace) -> SimpleNamespace:
    """Return an ORM-like verified payment instance."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        user_id=sample_user.id,
        amount=500,
        transaction_id="TXN12345678",
        proof_url="http://localhost:8000/static/payment-proofs/2026/proof.png",
        proof_path="payment-proofs/2026/proof.png",
        status=PaymentStatus.VERIFIED.value,
        payment_channel=PaymentChannel.ONLINE.value,
        capture_source=PaymentCaptureSource.WEBSITE.value,
        package_type=PackageType.COMBO.value,
        year=2026,
        verified_at=now,
        verified_by="admin",
        verification_note="Verified",
        rejected_at=None,
        rejection_reason=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_event() -> SimpleNamespace:
    """Return an ORM-like individual event instance."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=5)
    return SimpleNamespace(
        id=uuid4(),
        name="CAD Master",
        year=2026,
        type="TECHNICAL",
        category=EventCategory.EVENT.value,
        day_label="Day 1",
        date=start,
        end_date=start + timedelta(hours=2),
        is_all_day=False,
        description="3D modelling challenge",
        rules_url="https://example.com/rules.pdf",
        submission_url=None,
        submission_deadline=None,
        requires_document_submission=False,
        coordinator_name="Karthik",
        coordinator_phone="9876543211",
        trainer_name=None,
        contact_name=None,
        contact_phone=None,
        participation_mode=EventParticipationMode.INDIVIDUAL.value,
        team_min_size=None,
        team_max_size=None,
        max_teams=None,
        max_participants=50,
        is_active=True,
        is_archived=False,
        is_template=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_team_event() -> SimpleNamespace:
    """Return an ORM-like team event instance."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=6)
    return SimpleNamespace(
        id=uuid4(),
        name="Paper Presentation",
        year=2026,
        type="FLAGSHIP",
        category=EventCategory.EVENT.value,
        day_label="Day 2",
        date=start,
        end_date=start + timedelta(hours=3),
        is_all_day=False,
        description="Technical paper presentation",
        rules_url="https://example.com/paper-rules.pdf",
        submission_url=None,
        submission_deadline=start - timedelta(days=1),
        requires_document_submission=True,
        coordinator_name="Anitha",
        coordinator_phone="9876543212",
        trainer_name=None,
        contact_name=None,
        contact_phone=None,
        participation_mode=EventParticipationMode.TEAM.value,
        team_min_size=2,
        team_max_size=4,
        max_teams=25,
        max_participants=100,
        is_active=True,
        is_archived=False,
        is_template=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_team(
    sample_team_event: SimpleNamespace,
    sample_user: SimpleNamespace,
) -> SimpleNamespace:
    """Return an ORM-like open team instance."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        event_id=sample_team_event.id,
        name="Mech Innovators",
        name_normalized="MECH INNOVATORS",
        team_code="AB23CD",
        join_code="JOIN2026",
        join_code_expires_at=now + timedelta(days=7),
        status=TeamStatus.OPEN.value,
        member_count=1,
        leader_user_id=sample_user.id,
        leader_contact_phone_snapshot=sample_user.phone,
        leader_contact_email_snapshot=sample_user.email,
        locked_at=None,
        locked_by=None,
        cancelled_at=None,
        members=[],
        created_at=now,
        updated_at=now,
    )

"""
Integration test — full participant lifecycle.

Covers:
  1. Register a user
  2. Create a PENDING payment
  3. Admin approves the payment (allocates Shackles ID + QR token)
  4. Admin creates an event
  5. User registers for the event
  6. Scanner decodes the user's QR payload
  7. Scanner issues the kit (idempotent via operation_id)
  8. Scanner marks event attendance

Run:
    uv run python integration_test.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from shackles.config import settings
from shackles.db.engine import SessionLocal
from shackles.models.enums import (
    EventCategory,
    EventParticipationMode,
    PackageType,
    PaymentCaptureSource,
    PaymentChannel,
)
from shackles.schemas.event import EventCreate
from shackles.schemas.payment import PaymentCreate, PaymentVerify
from shackles.schemas.user import UserCreate
from shackles.services.auth_service import AuthService
from shackles.services.event_service import EventService
from shackles.services.payment_service import PaymentService
from shackles.services.qr import encode_qr_payload
from shackles.services.registration_service import RegistrationService
from shackles.services.scanner_service import ScannerService


def _random_phone() -> str:
    """Generate a random valid Indian mobile number (10 digits, starts with 9)."""
    return "9" + str(uuid.uuid4().int % 10**9).zfill(9)


async def main() -> None:
    async with SessionLocal() as session:
        auth = AuthService(session)
        payments = PaymentService(session)
        events = EventService(session)
        registrations = RegistrationService(session)
        scanner = ScannerService(session)

        # ------------------------------------------------------------------
        # 1. Register a user
        # ------------------------------------------------------------------
        email = f"test_{uuid.uuid4().hex[:6]}@example.com"
        print(f"1. Creating user {email}")
        user = await auth.register(UserCreate(
            first_name="Alice",
            last_name="Integration",
            email=email,
            phone=_random_phone(),
            password="Password123!",
            college_name="Test College",
            college_loc="City",
            department="IT",
            year_of_study="IV",
            gender="FEMALE",
        ))
        await session.commit()
        print(f"   User ID: {user.id}")

        # ------------------------------------------------------------------
        # 2. Submit a payment
        # ------------------------------------------------------------------
        print("2. Submitting payment")
        payment = await payments.create_for_user(
            user_id=user.id,
            data=PaymentCreate(
                amount=500,
                transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                proof_url="https://example.com/proof.jpg",
                proof_path="fake/path.jpg",
                capture_source=PaymentCaptureSource.WEBSITE,
                payment_channel=PaymentChannel.ONLINE,
                package_type=PackageType.EVENT_ONLY,
                year=settings.active_year,
            ),
        )
        await session.commit()
        print(f"   Payment status: {payment.status}")

        # ------------------------------------------------------------------
        # 3. Admin approves payment (allocates Shackles ID + QR token)
        # ------------------------------------------------------------------
        print("3. Approving payment")
        # Note: in real flows, admin_id comes from an authenticated admin.
        # Here we reuse the participant's ID — the service layer doesn't
        # enforce roles; that's the API layer's job.
        admin_id = user.id
        user, qr_payload = await payments.verify(
            user_id=user.id,
            data=PaymentVerify(action="APPROVE", verification_note="Approved"),
            admin_id=admin_id,
        )
        await session.commit()

        print(f"   Shackles ID:  {user.shackles_id}")
        print(f"   QR token:     {(user.qr_token or '')[:16]}...")
        print(f"   Role:         {user.role}")
        print(f"   Reg type:     {qr_payload['registration_type']}")

        # ------------------------------------------------------------------
        # 4. Admin creates an event
        # ------------------------------------------------------------------
        print("4. Creating event")
        event_start = datetime.now(timezone.utc) + timedelta(days=7)
        event = await events.create_event(EventCreate(
            name=f"Test Event {uuid.uuid4().hex[:4]}",
            description="Integration test event",
            year=settings.active_year,
            category=EventCategory.EVENT,
            type="FLAGSHIP",
            participation_mode=EventParticipationMode.INDIVIDUAL,
            date=event_start,
            end_date=event_start + timedelta(hours=2),
            is_all_day=False,
        ))
        await session.commit()
        print(f"   Event ID: {event.id}")

        # ------------------------------------------------------------------
        # 5. User registers for the event
        # ------------------------------------------------------------------
        print("5. Registering for event")
        reg = await registrations.register_individual(
            user_id=user.id,
            event_id=event.id,
        )
        await session.commit()
        print(f"   Registration ID: {reg.id}")

        # ------------------------------------------------------------------
        # 6. Scanner decodes the user's QR payload
        # ------------------------------------------------------------------
        # Build the same payload that would be printed on the user's card.
        qr_data = encode_qr_payload(
            qr_token=user.qr_token or "",
            shackles_id=user.shackles_id,
            year=settings.active_year,
        )
        print("6. Decoding QR")
        decoded = await scanner.decode_and_lookup(qr_data)
        print(
            f"   Decoded: {decoded['user']['first_name']} "
            f"({decoded['user']['shackles_id']})"
        )
        print(f"   Registrations on record: {len(decoded['registrations'])}")
        print(f"   Kit status: {decoded['kit_status']}")

        # ------------------------------------------------------------------
        # 7. Scanner issues the kit
        # ------------------------------------------------------------------
        print("7. Issuing kit")
        kit_operation_id = f"test-kit-{uuid.uuid4().hex[:8]}"
        kit_res = await scanner.issue_kit(
            user_id=user.id,
            station_id="SCANNER:KIT_TEST",
            operation_id=kit_operation_id,
        )
        await session.commit()
        print(f"   Result: {kit_res.get('message', kit_res)}")

        # Idempotency check: re-issuing with the same operation_id
        kit_res_2 = await scanner.issue_kit(
            user_id=user.id,
            station_id="SCANNER:KIT_TEST",
            operation_id=kit_operation_id,
        )
        print(f"   Second attempt: {kit_res_2}")

        # ------------------------------------------------------------------
        # 8. Scanner marks event attendance
        # ------------------------------------------------------------------
        print("8. Marking attendance")
        att_res = await scanner.mark_attendance(
            user_id=user.id,
            event_id=event.id,
            station_id="SCANNER:ATTENDANCE_TEST",
            operation_id=f"test-att-{uuid.uuid4().hex[:8]}",
        )
        await session.commit()
        print(f"   Result: {att_res.get('message', att_res)}")

        # ------------------------------------------------------------------
        # 9. Verify final state
        # ------------------------------------------------------------------
        print("\n--- Verification ---")
        from shackles.repositories.event_registration_repo import (
            EventRegistrationRepository,
        )
        from shackles.repositories.user_repo import UserRepository

        fresh_user = await UserRepository(session).get(user.id)
        fresh_reg = await EventRegistrationRepository(
            session
        ).get_by_user_and_event(user.id, event.id)

        if fresh_user is not None:
            print(f"   Kit status:    {fresh_user.kit_status}")
            print(f"   Kit issued at: {fresh_user.kit_issued_at}")
            print(f"   Kit issued by: {fresh_user.kit_issued_by}")
        if fresh_reg is not None:
            print(f"   Attended:      {fresh_reg.attended}")
            print(f"   Attended at:   {fresh_reg.attended_at}")

        print("\nIntegration test complete.")


if __name__ == "__main__":
    asyncio.run(main())
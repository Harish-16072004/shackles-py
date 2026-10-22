"""ARQ job definitions.

Every job receives `ctx` (the ARQ context dict) plus its own arguments.
Jobs own their database sessions — ARQ runs in a separate process, so
we create a fresh session per job and dispose it when done.
"""

import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

from shackles.config import settings
from shackles.db.engine import SessionLocal
from shackles.repositories.user_repo import UserRepository
from shackles.services.email import send_email
from shackles.services.email_templates import render_email_template
from shackles.services.qr import encode_qr_payload, generate_qr_image


logger = logging.getLogger(__name__)


# ============================================================
# Storage helper (local only for now)
# ============================================================

def _save_to_storage(key: str, body: bytes) -> Path:
    """Write bytes to the local storage directory. Returns the path."""
    base = Path(settings.storage_local_root)
    absolute = base / key
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(body)
    return absolute


def _public_url_for_key(key: str) -> str:
    """Build a public URL for a stored object key."""
    return f"{settings.public_app_url}/static/{key}"


# ============================================================
# Job: send_email_job
# ============================================================

async def send_email_job(
    ctx: dict,
    template_name: str,
    to: str,
    context: dict,
) -> dict:
    """Render a template and send the email.

    Args:
        template_name: Key into email_templates registry.
        to: Recipient email address.
        context: Template variables; `subject` and `year` are honored.
    """
    subject = context.get("subject", "Shackles Symposium")
    html = render_email_template(template_name, context)
    result = await send_email(to, subject, html)
    if not result["success"]:
        # Raise so ARQ marks the job as failed and can retry
        raise RuntimeError(f"Email send failed: {result['error']}")
    logger.info("[job] email sent to=%s template=%s", to, template_name)
    return result


# ============================================================
# Job: generate_qr_job
# ============================================================

async def generate_qr_job(
    ctx: dict,
    user_id: str,
    qr_token: str,
    shackles_id: str,
    year: int,
) -> dict:
    """Generate a QR image, upload it, and update the user's row.

    Steps:
      1. Encode the USER payload.
      2. Render a PNG via qrcode.
      3. Save to local storage.
      4. Update `User.qr_path` and `User.qr_image_url`.
      5. Enqueue a payment-verified email with the QR image URL.

    Args:
        user_id: UUID string of the user.
        qr_token: The user's `qr_token` (lookup key embedded in the QR).
        shackles_id: Formatted Shackles ID (e.g., 'SH26G001').
        year: Active symposium year.
    """
    # 1. Encode payload
    payload = encode_qr_payload(qr_token, shackles_id, year)

    # 2. Render PNG
    png_bytes = generate_qr_image(payload)

    # 3. Save to storage
    key = f"qr-codes/{year}/{user_id}.png"
    _save_to_storage(key, png_bytes)
    public_url = _public_url_for_key(key)

    # 4. Update DB
    async with SessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get(UUID(user_id))
        if user is not None:
            user.qr_path = key
            user.qr_image_url = public_url
            await session.commit()
            user_email = user.email
            user_name = f"{user.first_name} {user.last_name}".strip()
        else:
            user_email = None
            user_name = ""

    logger.info("[job] QR generated for user=%s key=%s", user_id, key)

    # 5. Enqueue payment-verified email (with the QR image URL)
    if user_email:
        try:
            from shackles.workers.queue import enqueue_email_job

            await enqueue_email_job(
                template_name="payment_verified",
                to=user_email,
                context={
                    "subject": f"Payment Verified — Shackles {year}",
                    "user_name": user_name,
                    "shackles_id": shackles_id,
                    "package_type": "Event Access",
                    "year": year,
                    "qr_image_url": public_url,
                },
            )
        except Exception as exc:
            logger.warning("[job] could not enqueue follow-up email: %s", exc)

    return {"user_id": user_id, "key": key, "url": public_url}


# ============================================================
# Job: export_csv_job
# ============================================================

async def export_csv_job(
    ctx: dict,
    export_type: str,
    filename: str,
    csv_content: str,
) -> dict:
    """Persist a pre-rendered CSV to storage.

    The route handler builds the CSV synchronously for small exports.
    Large exports should build the CSV inside this job instead — the
    signature allows that by passing `csv_content=None` and letting
    the job do the work based on `export_type`.
    """
    key = f"exports/{filename}"
    _save_to_storage(key, csv_content.encode("utf-8"))
    url = _public_url_for_key(key)
    logger.info("[job] CSV export saved key=%s", key)
    return {"key": key, "url": url}


# ============================================================
# Job: cleanup_expired_invites_job (periodic)
# ============================================================

async def cleanup_expired_invites_job(ctx: dict) -> dict:
    """Delete expired team invites.

    Intended to run via ARQ cron (e.g., daily at 3 AM).
    """
    from shackles.repositories.team_invite_repo import TeamInviteRepository

    async with SessionLocal() as session:
        repo = TeamInviteRepository(session)
        deleted = await repo.delete_expired()
        await session.commit()
    logger.info("[job] cleanup deleted %d expired invites", deleted)
    return {"deleted": deleted}
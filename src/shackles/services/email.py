"""Email sending — Resend API, SMTP (MailHog/production), and console fallback."""

from email.message import EmailMessage
import logging
import smtplib
from typing import Any

import httpx

from shackles.config import settings


logger = logging.getLogger(__name__)


_RESEND_ENDPOINT = "https://api.resend.com/emails"


async def _send_via_smtp(to: str, subject: str, html: str) -> dict[str, Any]:
    """Send an email over SMTP using aiosmtplib (or stdlib smtplib fallback)."""
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Please view this message in an HTML-capable email client.")
    msg.add_alternative(html, subtype="html")

    try:
        import aiosmtplib  # type: ignore[import-not-found]

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host or "localhost",
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
        )
        return {"success": True, "message_id": "smtp", "error": None}
    except ImportError:
        try:
            with smtplib.SMTP(
                settings.smtp_host or "localhost", settings.smtp_port, timeout=10
            ) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return {"success": True, "message_id": "smtp-stdlib", "error": None}
        except Exception as exc:
            logger.warning("[EMAIL:smtp-error] to=%s error=%s", to, exc)
            return {"success": False, "message_id": None, "error": str(exc)}
    except Exception as exc:
        logger.warning("[EMAIL:smtp-error] to=%s error=%s", to, exc)
        return {"success": False, "message_id": None, "error": str(exc)}


async def send_email(
    to: str,
    subject: str,
    html: str,
) -> dict[str, Any]:
    """Send a single email.

    Priority:
      1. Resend HTTP API if `settings.resend_api_key` is configured.
      2. SMTP (e.g., MailHog in local dev) if `settings.smtp_host` is configured.
      3. Console stdout fallback for zero-dependency development.

    Returns:
        {"success": bool, "message_id": str | None, "error": str | None}
    """
    if settings.resend_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    _RESEND_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {settings.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": settings.email_from,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                    },
                )
            if not resp.is_success:
                return {
                    "success": False,
                    "message_id": None,
                    "error": f"Resend error {resp.status_code}: {resp.text}",
                }
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("id"),
                "error": None,
            }
        except httpx.HTTPError as exc:
            logger.warning("[EMAIL:error] to=%s error=%s", to, exc)
            return {
                "success": False,
                "message_id": None,
                "error": str(exc),
            }

    if settings.smtp_host:
        return await _send_via_smtp(to, subject, html)

    logger.info(
        "[EMAIL:console] to=%s subject=%s\n%s",
        to,
        subject,
        html[:400],
    )
    return {
        "success": True,
        "message_id": "console-fallback",
        "error": None,
    }


async def send_email_batch(
    recipients: list[str],
    subject: str,
    html: str,
) -> list[dict[str, Any]]:
    """Send the same email to multiple recipients independently.

    Individual failures do not stop the batch.
    """
    results = []
    for recipient in recipients:
        result = await send_email(recipient, subject, html)
        results.append({"email": recipient, **result})
    return results
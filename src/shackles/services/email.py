"""Email sending — Resend API with console fallback."""

import logging
from typing import Any

import httpx

from shackles.config import settings


logger = logging.getLogger(__name__)


_RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_email(
    to: str,
    subject: str,
    html: str,
) -> dict[str, Any]:
    """Send a single email.

    Uses Resend if `settings.resend_api_key` is set. Otherwise logs the
    email to stdout (development fallback) so local flows can be tested
    without an API key.

    Returns:
        {"success": bool, "message_id": str | None, "error": str | None}
    """
    if not settings.resend_api_key:
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
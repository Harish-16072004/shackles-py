"""Notification helpers — enqueue email jobs via ARQ.

Each function builds a template context and hands off to the worker.
This keeps the request handler fast — the actual email rendering and
sending happens in the worker process.
"""

import logging

from shackles.config import settings
from shackles.workers.queue import enqueue_email_job


logger = logging.getLogger(__name__)


# ============================================================
# Payment
# ============================================================

async def notify_payment_verified(
    *,
    user_email: str,
    user_name: str,
    shackles_id: str,
    package_type: str,
    year: int,
    qr_image_url: str | None = None,
) -> None:
    """Enqueue a payment-verified email.

    Note: when called from the payment verify flow, prefer the
    `generate_qr_job` path which sends this email *after* the QR image
    is available.
    """
    await enqueue_email_job(
        template_name="payment_verified",
        to=user_email,
        context={
            "subject": f"Payment Verified — Shackles {year}",
            "user_name": user_name,
            "shackles_id": shackles_id,
            "package_type": package_type,
            "year": year,
            "qr_image_url": qr_image_url,
        },
    )


# ============================================================
# Teams
# ============================================================

async def notify_team_created(
    *,
    leader_email: str,
    leader_name: str,
    team_name: str,
    event_name: str,
    team_code: str,
    join_code: str,
    join_url: str,
) -> None:
    """Enqueue a team-created email for the leader."""
    await enqueue_email_job(
        template_name="team_created",
        to=leader_email,
        context={
            "subject": f"Team Created: {team_name}",
            "leader_name": leader_name,
            "team_name": team_name,
            "event_name": event_name,
            "team_code": team_code,
            "join_code": join_code,
            "join_url": join_url,
            "year": settings.active_year,
        },
    )


async def notify_team_locked(
    *,
    member_email: str,
    member_name: str,
    team_name: str,
    event_name: str,
    team_code: str,
) -> None:
    """Enqueue a team-locked email for one member."""
    await enqueue_email_job(
        template_name="team_locked",
        to=member_email,
        context={
            "subject": f"Team Locked: {event_name}",
            "member_name": member_name,
            "team_name": team_name,
            "event_name": event_name,
            "team_code": team_code,
            "year": settings.active_year,
        },
    )


async def notify_member_joined(
    *,
    member_email: str,
    member_name: str,
    team_name: str,
    event_name: str,
    leader_name: str,
) -> None:
    """Enqueue a member-joined email."""
    await enqueue_email_job(
        template_name="member_joined",
        to=member_email,
        context={
            "subject": f"Joined Team: {team_name}",
            "member_name": member_name,
            "team_name": team_name,
            "event_name": event_name,
            "leader_name": leader_name,
            "year": settings.active_year,
        },
    )


# ============================================================
# Papers
# ============================================================

async def notify_abstract_upload_request(
    *,
    member_email: str,
    member_name: str,
    team_name: str,
    event_name: str,
    team_id: str,
    abstract_deadline: str | None,
    is_leader: bool,
) -> None:
    """Enqueue an abstract-upload-request email."""
    await enqueue_email_job(
        template_name="abstract_upload_request",
        to=member_email,
        context={
            "subject": f"Abstract Submission Required — {event_name}",
            "member_name": member_name,
            "team_name": team_name,
            "event_name": event_name,
            "abstract_deadline": abstract_deadline,
            "is_leader": is_leader,
            "year": settings.active_year,
        },
    )


async def notify_paper_selection_result(
    *,
    member_email: str,
    member_name: str,
    team_name: str,
    event_name: str,
    selection_status: str,
    selection_note: str | None = None,
    presentation_deadline: str | None = None,
) -> None:
    """Enqueue a paper-selection-result email."""
    subject_prefix = (
        "Abstract Selected" if selection_status == "SELECTED"
        else "Abstract Review Result"
    )
    await enqueue_email_job(
        template_name="paper_selection_result",
        to=member_email,
        context={
            "subject": f"{subject_prefix} — {event_name}",
            "member_name": member_name,
            "team_name": team_name,
            "event_name": event_name,
            "selection_status": selection_status,
            "selection_note": selection_note,
            "presentation_deadline": presentation_deadline,
            "year": settings.active_year,
        },
    )


# ============================================================
# Entry passes
# ============================================================

async def notify_entry_pass(
    *,
    participant_email: str,
    participant_name: str,
    event_name: str,
    qr_image_url: str,
    qr_token: str,
) -> None:
    """Enqueue an entry-pass email."""
    await enqueue_email_job(
        template_name="generic",
        to=participant_email,
        context={
            "subject": f"Entry Pass — {event_name}",
            "message": (
                f"Hi {participant_name}, your entry pass for {event_name} "
                f"is ready. Your QR code is available at: {qr_image_url}"
            ),
            "year": settings.active_year,
        },
    )
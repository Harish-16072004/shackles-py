"""ARQ pool management and enqueue helpers.

The pool is created once in the FastAPI lifespan and reused for the
lifetime of the process. Enqueue helpers are safe to call from any
service — failures are logged and swallowed so a Redis hiccup does not
break user requests.
"""

import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from shackles.config import settings


logger = logging.getLogger(__name__)


_pool: ArqRedis | None = None


# ============================================================
# Lifecycle
# ============================================================

async def init_arq_pool() -> ArqRedis:
    """Create the shared ARQ pool. Called from FastAPI lifespan."""
    global _pool
    if _pool is not None:
        return _pool
    _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    logger.info("[arq] pool initialized at %s", settings.redis_url)
    return _pool


async def close_arq_pool() -> None:
    """Close the shared pool. Called from FastAPI lifespan shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("[arq] pool closed")


async def _get_pool() -> ArqRedis:
    if _pool is None:
        # Lazy-init: first enqueue call might happen before startup ran
        # (e.g., in tests). Safe to call again.
        return await init_arq_pool()
    return _pool


# ============================================================
# Enqueue helpers
# ============================================================

async def enqueue_email_job(
    template_name: str,
    to: str,
    context: dict,
) -> str | None:
    """Enqueue a templated email. Returns the ARQ job ID, or None on failure."""
    try:
        pool = await _get_pool()
        job = await pool.enqueue_job(
            "send_email_job", template_name, to, context
        )
        if job is None:
            logger.warning("[arq] email job was not enqueued")
            return None
        logger.info(
            "[arq] enqueued email job id=%s template=%s to=%s",
            job.job_id,
            template_name,
            to,
        )
        return job.job_id
    except Exception as exc:
        logger.warning("[arq] failed to enqueue email job: %s", exc)
        return None


async def enqueue_qr_generation(
    user_id: str,
    qr_token: str,
    shackles_id: str,
    year: int,
) -> str | None:
    """Enqueue a QR generation job for a user."""
    try:
        pool = await _get_pool()
        job = await pool.enqueue_job(
            "generate_qr_job", user_id, qr_token, shackles_id, year
        )
        if job is None:
            logger.warning("[arq] QR job was not enqueued")
            return None
        logger.info(
            "[arq] enqueued QR job id=%s user=%s", job.job_id, user_id
        )
        return job.job_id
    except Exception as exc:
        logger.warning("[arq] failed to enqueue QR job: %s", exc)
        return None


async def enqueue_csv_export(
    export_type: str,
    filename: str,
    csv_content: str,
) -> str | None:
    """Enqueue a CSV export job."""
    try:
        pool = await _get_pool()
        job = await pool.enqueue_job(
            "export_csv_job", export_type, filename, csv_content
        )
        if job is None:
            return None
        return job.job_id
    except Exception as exc:
        logger.warning("[arq] failed to enqueue CSV job: %s", exc)
        return None
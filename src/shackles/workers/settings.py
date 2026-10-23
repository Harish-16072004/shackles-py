"""ARQ WorkerSettings — run with:

    uv run arq shackles.workers.settings.WorkerSettings
"""

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from shackles.config import settings
from shackles.workers.jobs import (
    cleanup_expired_invites_job,
    export_csv_job,
    generate_qr_job,
    send_email_job,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def startup(ctx: dict[str, Any]) -> None:
    """Run once when the worker process starts."""
    print(f"[worker] connected to Redis at {settings.redis_url}")
    print(f"[worker] active year: {settings.active_year}")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run once when the worker shuts down."""
    print("[worker] shutting down")


class WorkerSettings:
    """Configuration passed to ARQ's Worker.

    Functions listed here are the only jobs the worker can execute.
    """

    functions = [
        send_email_job,
        generate_qr_job,
        export_csv_job,
        cleanup_expired_invites_job,
    ]

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    on_startup = startup
    on_shutdown = shutdown

    # Retry policy
    max_tries = 3
    job_timeout = 120  # seconds

    # Keep job results for 24 hours
    keep_result = 86400

    # How many jobs to run concurrently per worker
    max_jobs = 10

    # Daily cleanup of expired team invitations at 03:00 UTC
    cron_jobs = [
        cron(cleanup_expired_invites_job, hour=3, minute=0),
    ]
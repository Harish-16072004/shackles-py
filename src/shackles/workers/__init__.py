"""ARQ worker package.

The worker runs in a separate process and picks jobs off a Redis-backed
queue. Enqueue from the web app via `workers.queue.enqueue_*`; run the
worker process with:

    uv run arq shackles.workers.settings.WorkerSettings
"""
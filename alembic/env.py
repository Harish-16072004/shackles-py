"""
Alembic environment — async version.

Reads DATABASE_URL from shackles.config.settings, not from alembic.ini.
Imports Base.metadata so autogenerate sees all models.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Import application settings and metadata
# ---------------------------------------------------------------------------
# Make sure `src/` is on sys.path (configured via `prepend_sys_path` in alembic.ini)
from shackles.config import settings  # noqa: E402
from shackles.db.base import Base  # noqa: E402

# IMPORTANT: import every model module here so that Base.metadata is populated.
# Alembic's autogenerate compares Base.metadata against the DB — if a model
# isn't imported here, its table will show up as "to be dropped".
#
# When you add new model files under src/shackles/models/, add them to
# `src/shackles/models/__init__.py` — that single import below will pull
# in everything.
from shackles import models  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Inject the database URL from application settings.
# We use the sync URL form for Alembic's connection — async drivers like
# asyncpg are handled by async_engine_from_config below.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations — generate SQL without a live DB connection
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations — run against a live DB
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic context and run migrations against the connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,             # Detect column type changes
        compare_server_default=True,   # Detect server default changes
        render_as_batch=False,         # Not needed on Postgres
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — runs the async loop."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point — Alembic decides offline vs online based on context
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
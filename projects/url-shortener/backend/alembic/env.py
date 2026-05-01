"""Alembic env using the sync psycopg2 URL.

We deliberately use the sync driver here even though the app is async — async
Alembic is still rough and the standard pattern is to migrate via sync. The
URL comes from ALEMBIC_DATABASE_URL (preferred) or DATABASE_URL with the
asyncpg driver swapped out.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL")
    if url:
        return url
    async_url = os.environ.get("DATABASE_URL")
    if not async_url:
        raise RuntimeError(
            "Set ALEMBIC_DATABASE_URL (sync) or DATABASE_URL (async) in the environment"
        )
    return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

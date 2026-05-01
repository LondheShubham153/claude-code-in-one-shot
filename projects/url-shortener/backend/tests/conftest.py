"""Shared fixtures.

- A session-scoped Postgres via testcontainers (image pulled on first run).
- Migrations applied once per session.
- Function-scoped FastAPI app + httpx.AsyncClient.
- Autouse: monkeypatch Safe Browsing to skipped=True; tests opt back in via
  the `_restore_real_safe_browsing` fixture in test_safe_browsing.py.
- Autouse: monkeypatch Temporal client so signal_with_start is a no-op recorder.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

# Ensure tests don't touch a real .env
os.environ.setdefault("ENV", "test")
os.environ.setdefault("PUBLIC_BASE_URL", "http://test.local")
os.environ.setdefault("RATE_LIMIT_SHORTEN", "10/minute")


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    raw_url = container.get_connection_url()  # postgresql+psycopg2://...
    sync_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg2://")
    async_url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    os.environ["DATABASE_URL"] = async_url
    os.environ["ALEMBIC_DATABASE_URL"] = sync_url

    # Apply migrations. Use sys.executable -m alembic so we don't need
    # the venv's bin/ on PATH (calling .venv/bin/pytest directly omits it).
    repo_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=repo_root,
        env={**os.environ, "ALEMBIC_DATABASE_URL": sync_url},
    )

    yield container
    container.stop()


@pytest_asyncio.fixture
async def reset_engine():
    """Tear down cached engine between tests so DATABASE_URL changes apply."""
    from app.db import reset_engine_for_tests

    await reset_engine_for_tests()
    yield
    await reset_engine_for_tests()


@pytest.fixture(autouse=True)
def patch_safe_browsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: every test sees Safe Browsing as skipped (no API key).
    Tests that need the real client opt back in by setting SAFE_BROWSING_API_KEY
    and using respx to mock the HTTP call.
    """
    from app.services import safe_browsing

    monkeypatch.setattr(
        safe_browsing,
        "check_url",
        AsyncMock(return_value=safe_browsing.SafeBrowsingResult(safe=True, skipped=True)),
    )


@pytest.fixture(autouse=True)
def patch_temporal_signal(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Default: signal_click is a recorded no-op so HTTP tests don't need a real Temporal."""
    mock = AsyncMock()
    monkeypatch.setattr("app.routers.redirect.signal_click", mock)
    return mock


@pytest_asyncio.fixture
async def client(pg_container: PostgresContainer, reset_engine) -> AsyncIterator[httpx.AsyncClient]:  # noqa: ARG001
    # Import inside the fixture so settings pick up the env updated by pg_container.
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test.local") as c:
        # Manually run lifespan-equivalent — we don't have a real Temporal here,
        # so skip the lifespan to avoid the connect() call. The patch_temporal_signal
        # fixture already replaces the only call site we exercise.
        yield c


@pytest_asyncio.fixture
async def db_session(pg_container: PostgresContainer, reset_engine):  # noqa: ARG001
    from app.db import get_sessionmaker

    sm = get_sessionmaker()
    async with sm() as session:
        yield session

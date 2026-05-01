from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz(client) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_db_ok_temporal_unreachable(client, monkeypatch) -> None:
    """No Temporal server is up in unit tests, so the temporal probe should report
    'down' and overall status should be 'degraded'. DB should be 'ok' (testcontainers).
    """

    async def _boom() -> None:
        raise RuntimeError("temporal unreachable in tests")

    monkeypatch.setattr("app.routers.health.get_temporal_client", _boom)
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] == "ok"
    assert body["temporal"] == "down"
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_readyz_temporal_ok(client, monkeypatch) -> None:
    async def _ok():  # noqa: ANN202
        return object()

    monkeypatch.setattr("app.routers.health.get_temporal_client", _ok)
    resp = await client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["temporal"] == "ok"

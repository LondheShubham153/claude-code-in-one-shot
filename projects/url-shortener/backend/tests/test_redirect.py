from __future__ import annotations

import pytest
from sqlalchemy import update

from app.models import Link


@pytest.mark.asyncio
async def test_redirect_302_and_signals(client, patch_temporal_signal) -> None:
    create = await client.post("/api/links", json={"url": "https://example.com/x"})
    slug = create.json()["slug"]

    resp = await client.get(f"/s/{slug}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://example.com/x")
    patch_temporal_signal.assert_awaited_once_with(slug)


@pytest.mark.asyncio
async def test_redirect_404_unknown(client) -> None:
    resp = await client.get("/s/nonexistent", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_410_disabled(client, db_session) -> None:
    create = await client.post("/api/links", json={"url": "https://example.com/y"})
    slug = create.json()["slug"]
    await db_session.execute(update(Link).where(Link.slug == slug).values(disabled=True))
    await db_session.commit()

    resp = await client.get(f"/s/{slug}", follow_redirects=False)
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_redirect_falls_back_when_signal_fails(
    client, monkeypatch, db_session
) -> None:
    create = await client.post("/api/links", json={"url": "https://example.com/z"})
    slug = create.json()["slug"]

    async def _boom(_slug: str) -> None:
        raise RuntimeError("temporal unavailable")

    monkeypatch.setattr("app.routers.redirect.signal_click", _boom)

    resp = await client.get(f"/s/{slug}", follow_redirects=False)
    assert resp.status_code == 302  # still redirects

    # Sync fallback should have incremented click_count
    await db_session.commit()  # release any held tx
    refreshed = await client.get(f"/api/links/{slug}")
    assert refreshed.json()["click_count"] == 1

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_lookup_returns_metadata(client) -> None:
    create = await client.post("/api/links", json={"url": "https://example.com/foo"})
    slug = create.json()["slug"]

    resp = await client.get(f"/api/links/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == slug
    assert body["click_count"] == 0
    assert body["disabled"] is False


@pytest.mark.asyncio
async def test_lookup_404(client) -> None:
    resp = await client.get("/api/links/missing")
    assert resp.status_code == 404

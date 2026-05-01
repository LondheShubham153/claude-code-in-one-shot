from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import safe_browsing


@pytest.mark.asyncio
async def test_shorten_golden_path(client) -> None:
    resp = await client.post("/api/links", json={"url": "https://example.com/long/path"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["slug"]) >= 7
    assert body["url"].startswith("https://example.com")
    assert body["short_url"].endswith(f"/s/{body['slug']}")
    assert body["click_count"] == 0
    assert body["disabled"] is False


@pytest.mark.asyncio
async def test_shorten_rejects_private_ip(client) -> None:
    resp = await client.post("/api/links", json={"url": "http://169.254.169.254/"})
    assert resp.status_code == 400
    assert "blocked" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_shorten_rejects_disallowed_scheme(client) -> None:
    resp = await client.post("/api/links", json={"url": "ftp://example.com"})
    # Pydantic HttpUrl rejects ftp at the schema layer (422), not our validator (400).
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_shorten_rejects_unsafe_url(client, monkeypatch) -> None:
    # Use a resolvable host so url_validator passes; mock safe_browsing to flag it.
    monkeypatch.setattr(
        "app.routers.links.safe_browsing_check",
        AsyncMock(
            return_value=safe_browsing.SafeBrowsingResult(
                safe=False, skipped=False, threat_types=["MALWARE"]
            )
        ),
    )
    resp = await client.post("/api/links", json={"url": "https://example.com/payload"})
    assert resp.status_code == 400
    assert "unsafe_url" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_custom_slug_accepted(client) -> None:
    resp = await client.post(
        "/api/links",
        json={"url": "https://example.com", "custom_slug": "myslug123"},
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "myslug123"


@pytest.mark.asyncio
async def test_custom_slug_reserved_rejected(client) -> None:
    resp = await client.post(
        "/api/links",
        json={"url": "https://example.com", "custom_slug": "admin"},
    )
    assert resp.status_code == 422

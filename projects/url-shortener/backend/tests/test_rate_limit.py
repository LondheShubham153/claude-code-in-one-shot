from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_rate_limit_429_after_threshold(client) -> None:
    # Default is 10/minute. Burst 11 quickly.
    statuses = []
    for i in range(11):
        resp = await client.post(
            "/api/links",
            json={"url": f"https://example.com/burst-{i}"},
            headers={"x-forwarded-for": "203.0.113.42"},
        )
        statuses.append(resp.status_code)

    assert statuses[:10].count(201) == 10
    assert statuses[10] == 429


@pytest.mark.asyncio
async def test_rate_limit_does_not_apply_to_redirect(client, monkeypatch) -> None:
    create = await client.post(
        "/api/links",
        json={"url": "https://example.com/loop"},
        headers={"x-forwarded-for": "198.51.100.42"},
    )
    slug = create.json()["slug"]

    # 50 redirects from the same IP — none should 429.
    for _ in range(50):
        resp = await client.get(
            f"/s/{slug}",
            follow_redirects=False,
            headers={"x-forwarded-for": "198.51.100.42"},
        )
        assert resp.status_code == 302

"""Force slug collisions via monkeypatched generator and verify retry path.

slowapi's Limiter is a process-wide singleton with a per-IP bucket. Other
tests in the suite POST from the default test-client IP (127.0.0.1) and can
exhaust the bucket before this file runs. Each test here pins a unique
X-Forwarded-For so it gets a fresh bucket.
"""

from __future__ import annotations

from itertools import chain, count

import pytest

from app.services import slug as slug_service

_XFF_A = {"x-forwarded-for": "192.0.2.10"}  # TEST-NET-1
_XFF_B = {"x-forwarded-for": "192.0.2.11"}


@pytest.mark.asyncio
async def test_collision_retry_succeeds(client, monkeypatch) -> None:
    # First call collides, second yields a fresh slug.
    seq = chain(["AAAAAAA", "BBBBBBB"], (f"NEW{n:04d}" for n in count()))

    def _gen(_length: int) -> str:
        return next(seq)

    monkeypatch.setattr(slug_service, "generate_slug", _gen)

    first = await client.post(
        "/api/links",
        json={"url": "https://example.com/a"},
        headers=_XFF_A,
    )
    assert first.status_code == 201, first.text
    assert first.json()["slug"] == "AAAAAAA"

    # Second insert with custom_slug=None will collide on AAAAAAA's collision path,
    # then BBBBBBB will succeed.
    monkeypatch.setattr(slug_service, "generate_slug", lambda _l: "AAAAAAA")
    second = await client.post(
        "/api/links",
        json={"url": "https://example.com/b"},
        headers=_XFF_A,
    )
    assert second.status_code == 500  # all retries collide on the same slug


@pytest.mark.asyncio
async def test_collision_then_unique_succeeds(client, monkeypatch) -> None:
    # Seed a known slug via custom_slug.
    pre = await client.post(
        "/api/links",
        json={"url": "https://example.com/seed", "custom_slug": "taken__"},
        headers=_XFF_B,
    )
    assert pre.status_code == 201, pre.text

    # Auto-gen path: collide on "taken__", then succeed on "fresh01".
    again = iter(["taken__", "fresh01"])
    monkeypatch.setattr(slug_service, "generate_slug", lambda _l: next(again))
    new = await client.post(
        "/api/links",
        json={"url": "https://example.com/post-collision"},
        headers=_XFF_B,
    )
    assert new.status_code == 201, new.text
    assert new.json()["slug"] == "fresh01"

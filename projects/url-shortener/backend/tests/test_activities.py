"""Direct tests for Temporal activities — they're plain async functions, so
we can call them via ActivityEnvironment without spinning up a workflow."""

from __future__ import annotations

import pytest
from temporalio.testing import ActivityEnvironment

from app.temporal.activities import (
    BatchInput,
    FlushInput,
    LinkRow,
    RecheckInput,
    disable_link,
    flush_click_count,
    list_active_links_batch,
    recheck_url_safety,
)


@pytest.mark.asyncio
async def test_flush_click_count_unknown_slug(client) -> None:  # noqa: ARG001
    env = ActivityEnvironment()
    new_count = await env.run(flush_click_count, FlushInput(slug="missing-slug-xx", delta=3))
    assert new_count == -1


@pytest.mark.asyncio
async def test_flush_click_count_zero_delta_noops(client) -> None:  # noqa: ARG001
    env = ActivityEnvironment()
    new_count = await env.run(flush_click_count, FlushInput(slug="anything", delta=0))
    assert new_count == -1


@pytest.mark.asyncio
async def test_flush_click_count_increments(client) -> None:
    create = await client.post(
        "/api/links",
        json={"url": "https://example.com/activity-test"},
        headers={"x-forwarded-for": "192.0.2.20"},
    )
    slug = create.json()["slug"]

    env = ActivityEnvironment()
    new_count = await env.run(flush_click_count, FlushInput(slug=slug, delta=5))
    assert new_count == 5

    new_count = await env.run(flush_click_count, FlushInput(slug=slug, delta=2))
    assert new_count == 7


@pytest.mark.asyncio
async def test_list_active_links_batch_excludes_disabled(client, db_session) -> None:
    from sqlalchemy import update

    from app.models import Link

    a = await client.post(
        "/api/links",
        json={"url": "https://example.com/active-1"},
        headers={"x-forwarded-for": "192.0.2.21"},
    )
    b = await client.post(
        "/api/links",
        json={"url": "https://example.com/disabled-2"},
        headers={"x-forwarded-for": "192.0.2.21"},
    )
    await db_session.execute(
        update(Link).where(Link.slug == b.json()["slug"]).values(disabled=True)
    )
    await db_session.commit()

    env = ActivityEnvironment()
    rows = await env.run(list_active_links_batch, BatchInput(offset=0, limit=100))
    slugs = {r.slug if hasattr(r, "slug") else r.id for r in rows}
    # rows is list[LinkRow] which has id+url, no slug. Just verify counts:
    assert any(r.id and "active-1" in r.url for r in rows)
    assert not any("disabled-2" in r.url for r in rows)


@pytest.mark.asyncio
async def test_disable_link_idempotent(client, db_session) -> None:
    from sqlalchemy import select

    from app.models import Link

    create = await client.post(
        "/api/links",
        json={"url": "https://example.com/to-disable"},
        headers={"x-forwarded-for": "192.0.2.22"},
    )
    slug = create.json()["slug"]
    row = (await db_session.execute(select(Link).where(Link.slug == slug))).scalar_one()
    link_id = row.id

    env = ActivityEnvironment()
    first = await env.run(disable_link, link_id)
    assert first is True  # actually flipped

    second = await env.run(disable_link, link_id)
    assert second is False  # already disabled, no-op


@pytest.mark.asyncio
async def test_recheck_url_safety_returns_skipped_when_no_api_key(
    client, monkeypatch  # noqa: ARG001
) -> None:
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    env = ActivityEnvironment()
    result = await env.run(
        recheck_url_safety, RecheckInput(link_id=1, url="https://example.com")
    )
    # When the API key is unset, check_url returns skipped=True; activity reports flagged=False
    assert result.flagged is False
    assert result.threat_types == []

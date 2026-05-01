"""Temporal activities — non-deterministic side effects live here.

All activities are async because we use asyncpg + httpx, both of which are
async-safe. No blocking I/O. Activities are registered in worker.py.

Idempotency notes:
- `flush_click_count` is delta-based (UPDATE += :n). Re-runs cause at-most a
  single flush worth of double-add (≤100 events). For exact-once we'd need a
  per-flush UUID + dedupe table — Phase 2.
- `disable_link` is fully idempotent (UPDATE WHERE disabled=false).
- `recheck_url_safety` is read-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update
from temporalio import activity

from app.db import get_sessionmaker
from app.models import Link
from app.services.safe_browsing import check_url

logger = logging.getLogger(__name__)


@dataclass
class FlushInput:
    slug: str
    delta: int


@dataclass
class RecheckInput:
    link_id: int
    url: str


@dataclass
class RecheckResult:
    link_id: int
    flagged: bool
    threat_types: list[str]


@dataclass
class BatchInput:
    offset: int
    limit: int


@dataclass
class LinkRow:
    id: int
    url: str


@activity.defn(name="flush_click_count")
async def flush_click_count(payload: FlushInput) -> int:
    """Add `delta` to click_count for `slug`. Returns the new value or -1 if missing."""
    if payload.delta <= 0:
        return -1
    sm = get_sessionmaker()
    async with sm() as session:
        result = await session.execute(
            update(Link)
            .where(Link.slug == payload.slug)
            .values(click_count=Link.click_count + payload.delta)
            .returning(Link.click_count)
        )
        row = result.first()
        await session.commit()
        if row is None:
            activity.logger.warning("flush_click_count: slug not found", extra={"slug": payload.slug})
            return -1
        return int(row[0])


@activity.defn(name="list_active_links_batch")
async def list_active_links_batch(payload: BatchInput) -> list[LinkRow]:
    """Return non-disabled links for the recheck workflow, paginated by id."""
    sm = get_sessionmaker()
    async with sm() as session:
        stmt = (
            select(Link.id, Link.url)
            .where(Link.disabled.is_(False))
            .order_by(Link.id)
            .offset(payload.offset)
            .limit(payload.limit)
        )
        result = await session.execute(stmt)
        return [LinkRow(id=row.id, url=row.url) for row in result]


@activity.defn(name="recheck_url_safety")
async def recheck_url_safety(payload: RecheckInput) -> RecheckResult:
    """Run a Safe Browsing check on a single URL. Lets Temporal retry policy
    handle Google's 429/5xx — see ClickCounterWorkflow's RetryPolicy in workflows.py.
    """
    activity.heartbeat(payload.link_id)
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        result = await check_url(payload.url, client=client)
    return RecheckResult(
        link_id=payload.link_id,
        flagged=not result.safe and not result.skipped,
        threat_types=result.threat_types,
    )


@activity.defn(name="disable_link")
async def disable_link(link_id: int) -> bool:
    """Idempotent — only flips `disabled` from false to true. Returns whether
    the row was actually changed."""
    sm = get_sessionmaker()
    async with sm() as session:
        result = await session.execute(
            update(Link)
            .where(Link.id == link_id, Link.disabled.is_(False))
            .values(disabled=True, safe_browsing_checked_at=datetime.now(tz=timezone.utc))
        )
        await session.commit()
        return result.rowcount > 0

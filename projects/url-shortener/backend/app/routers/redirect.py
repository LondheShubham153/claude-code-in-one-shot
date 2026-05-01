import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Link
from app.services.slug import lookup_by_slug
from app.temporal.client import signal_click

logger = logging.getLogger(__name__)
router = APIRouter(tags=["redirect"])


async def _sync_increment(session: AsyncSession, slug: str) -> None:
    """Fallback path when Temporal signaling fails — increment in DB directly."""
    await session.execute(
        update(Link).where(Link.slug == slug).values(click_count=Link.click_count + 1)
    )
    await session.commit()


@router.get("/s/{slug}")
async def redirect_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    link = await lookup_by_slug(session, slug)
    if link is None:
        raise HTTPException(status_code=404, detail="not_found")
    if link.disabled:
        raise HTTPException(
            status_code=410,
            detail="this link has been disabled because it was flagged as unsafe",
        )

    try:
        await signal_click(slug)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "temporal signal failed — falling back to sync DB increment", extra={"err": str(exc)}
        )
        try:
            await _sync_increment(session, slug)
        except Exception:  # noqa: BLE001
            logger.exception("sync click increment also failed — proceeding with redirect anyway")

    return RedirectResponse(url=link.url, status_code=302)

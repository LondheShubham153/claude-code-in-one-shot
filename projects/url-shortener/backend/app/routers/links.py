import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.rate_limit import limiter
from app.schemas import LinkOut, ShortenRequest
from app.services.safe_browsing import check_url as safe_browsing_check
from app.services.slug import (
    ReservedSlugError,
    SlugCollisionError,
    insert_link_with_retry,
    lookup_by_slug,
)
from app.services.url_validator import UnsafeURLError, validate_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["links"])


def _to_link_out(link, public_base_url: str) -> LinkOut:  # type: ignore[no-untyped-def]
    return LinkOut(
        slug=link.slug,
        url=link.url,
        short_url=f"{public_base_url.rstrip('/')}/s/{link.slug}",
        click_count=link.click_count,
        disabled=link.disabled,
        created_at=link.created_at,
    )


@router.post("/links", response_model=LinkOut, status_code=201)
@limiter.limit(get_settings().RATE_LIMIT_SHORTEN)
async def shorten(
    request: Request,
    payload: ShortenRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> LinkOut:
    settings = get_settings()
    url = str(payload.url)

    try:
        validate_url(url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=f"invalid_url: {exc}") from exc

    sb = await safe_browsing_check(url)
    if not sb.safe:
        logger.info("rejected unsafe url", extra={"threat_types": sb.threat_types})
        raise HTTPException(
            status_code=400,
            detail=f"unsafe_url: flagged as {','.join(sb.threat_types) or 'unsafe'}",
        )
    sb_checked_at = datetime.now(tz=timezone.utc) if not sb.skipped else None

    created_ip = None
    if request.client is not None:
        xff = request.headers.get("x-forwarded-for")
        created_ip = (xff.split(",")[0].strip() if xff else request.client.host) or None

    try:
        link = await insert_link_with_retry(
            session,
            url=url,
            custom_slug=payload.custom_slug,
            created_ip=created_ip,
            safe_browsing_checked_at=sb_checked_at,
        )
    except ReservedSlugError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SlugCollisionError as exc:
        raise HTTPException(status_code=500, detail="slug_generation_failed") from exc

    await session.commit()
    return _to_link_out(link, settings.PUBLIC_BASE_URL)


@router.get("/links/{slug}", response_model=LinkOut)
async def get_link(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> LinkOut:
    link = await lookup_by_slug(session, slug)
    if link is None:
        raise HTTPException(status_code=404, detail="not_found")
    return _to_link_out(link, get_settings().PUBLIC_BASE_URL)

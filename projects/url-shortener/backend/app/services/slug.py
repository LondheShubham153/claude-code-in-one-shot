import logging
import secrets
import string

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Link

logger = logging.getLogger(__name__)

_ALPHABET = string.ascii_letters + string.digits  # base62


class SlugCollisionError(RuntimeError):
    """Raised when collision retries are exhausted."""


class ReservedSlugError(ValueError):
    """Raised when a custom slug matches a reserved word."""


def generate_slug(length: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def insert_link_with_retry(
    session: AsyncSession,
    *,
    url: str,
    custom_slug: str | None,
    created_ip: str | None,
    safe_browsing_checked_at,  # type: ignore[no-untyped-def]
) -> Link:
    """Insert a Link, retrying on slug collision unless `custom_slug` is set."""
    settings = get_settings()
    base_length = settings.SLUG_LENGTH
    max_retries = settings.MAX_SLUG_RETRIES

    if custom_slug is not None:
        if custom_slug.lower() in settings.RESERVED_SLUGS:
            raise ReservedSlugError(f"slug '{custom_slug}' is reserved")
        link = Link(
            slug=custom_slug,
            url=url,
            created_ip=created_ip,
            safe_browsing_checked_at=safe_browsing_checked_at,
        )
        session.add(link)
        await session.flush()
        return link

    last_err: Exception | None = None
    # Try up to max_retries at base_length, then up to max_retries more at base_length+1
    for attempt in range(max_retries * 2):
        length = base_length + (1 if attempt >= max_retries else 0)
        slug = generate_slug(length)
        if slug.lower() in settings.RESERVED_SLUGS:
            continue
        link = Link(
            slug=slug,
            url=url,
            created_ip=created_ip,
            safe_browsing_checked_at=safe_browsing_checked_at,
        )
        session.add(link)
        try:
            await session.flush()
            return link
        except IntegrityError as exc:
            last_err = exc
            await session.rollback()
            logger.warning(
                "slug collision on attempt %d (slug=%s, length=%d) — retrying",
                attempt + 1,
                slug,
                length,
            )
            continue
    raise SlugCollisionError(f"exhausted slug retries: {last_err}")


async def lookup_by_slug(session: AsyncSession, slug: str) -> Link | None:
    stmt = select(Link).where(Link.slug == slug)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

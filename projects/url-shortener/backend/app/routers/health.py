import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.temporal.client import get_temporal_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_session)) -> dict[str, str]:  # noqa: B008
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("readyz: db check failed: %s", exc)
        db_status = "down"

    temporal_status = "ok"
    try:
        await get_temporal_client()
    except Exception as exc:  # noqa: BLE001
        logger.warning("readyz: temporal check failed: %s", exc)
        temporal_status = "down"

    overall = "ok" if db_status == "ok" and temporal_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "temporal": temporal_status}

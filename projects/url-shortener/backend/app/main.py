import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.logging_conf import configure_logging
from app.rate_limit import limiter
from app.routers import health, links, redirect
from app.temporal.client import close_temporal_client, get_temporal_client
from app.temporal.schedules import ensure_recheck_schedule

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    settings = get_settings()
    logger.info(
        "starting up",
        extra={
            "env": settings.ENV,
            "public_base_url": settings.PUBLIC_BASE_URL,
            "safe_browsing_enabled": bool(settings.SAFE_BROWSING_API_KEY),
            "temporal_host": settings.TEMPORAL_HOST,
        },
    )
    if not settings.SAFE_BROWSING_API_KEY:
        logger.warning(
            "SAFE_BROWSING_API_KEY is not set — both the synchronous shorten check "
            "and the daily recheck workflow will no-op. Set it in .env to enable."
        )
    # Connect Temporal and ensure the daily recheck schedule exists.
    try:
        client = await get_temporal_client()
        await ensure_recheck_schedule(client)
        logger.info("temporal client connected and recheck schedule ensured")
    except Exception:  # noqa: BLE001
        logger.exception("failed to connect Temporal client at startup — continuing")

    yield

    await close_temporal_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="URL Shortener",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": "conflict", "code": str(exc.orig)})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    app.include_router(health.router)
    app.include_router(links.router)
    app.include_router(redirect.router)
    return app


app = create_app()

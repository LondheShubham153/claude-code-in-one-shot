"""Temporal client singleton + helpers.

Used from FastAPI lifespan and from request handlers (e.g. the redirect router
signaling ClickCounterWorkflow). Failures here must not break the request —
callers fall back to a synchronous DB increment when signaling fails.
"""

from __future__ import annotations

import logging

from temporalio.client import Client

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    _client = await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)
    return _client


async def close_temporal_client() -> None:
    """Best-effort teardown for tests / shutdown. Temporal Python SDK Client
    doesn't expose an explicit close — clearing the singleton is enough."""
    global _client
    _client = None


def click_workflow_id(slug: str) -> str:
    return f"click-counter:{slug}"


async def signal_click(slug: str) -> None:
    """Signal-with-start the ClickCounterWorkflow for `slug`.

    Importing the workflow class lazily — avoids dragging the workflow module
    into request-handler code at import time.
    """
    from app.temporal.workflows import ClickCounterParams, ClickCounterWorkflow

    settings = get_settings()
    client = await get_temporal_client()
    await client.start_workflow(
        ClickCounterWorkflow.run,
        ClickCounterParams(
            slug=slug,
            flush_interval_seconds=settings.CLICK_FLUSH_INTERVAL_SECONDS,
            flush_threshold=settings.CLICK_FLUSH_THRESHOLD,
            continue_as_new_at=settings.CLICK_CONTINUE_AS_NEW_AT,
        ),
        id=click_workflow_id(slug),
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        start_signal="record_click",
    )

"""Temporal worker entrypoint.

Run inside the `worker` docker-compose service: `python -m app.temporal.worker`.
Registers both workflows + all activities on the configured task queue.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import get_settings
from app.logging_conf import configure_logging
from app.temporal.activities import (
    disable_link,
    flush_click_count,
    list_active_links_batch,
    recheck_url_safety,
)
from app.temporal.schedules import ensure_recheck_schedule
from app.temporal.workflows import ClickCounterWorkflow, SafeBrowsingRecheckWorkflow

logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging()
    settings = get_settings()
    logger.info("connecting to Temporal at %s", settings.TEMPORAL_HOST)
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    # Make sure the recheck schedule exists. Backend lifespan also does this;
    # the worker can run without the backend up, so do it here too.
    try:
        await ensure_recheck_schedule(client)
    except Exception:  # noqa: BLE001
        logger.exception("failed to ensure recheck schedule — continuing")

    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[ClickCounterWorkflow, SafeBrowsingRecheckWorkflow],
        activities=[
            flush_click_count,
            list_active_links_batch,
            recheck_url_safety,
            disable_link,
        ],
    )
    logger.info("Worker started on task_queue=%s", settings.TEMPORAL_TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

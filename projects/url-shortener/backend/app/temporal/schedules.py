"""Idempotent registration of the daily Safe Browsing recheck schedule.

Called from FastAPI lifespan startup. Safe to call repeatedly — uses
upsert semantics (try create, fall through to update on conflict).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

SCHEDULE_ID = "safe-browsing-recheck"


async def ensure_recheck_schedule(client: Client) -> None:
    settings = get_settings()
    from app.temporal.workflows import SafeBrowsingRecheckWorkflow  # avoid circular import

    schedule = Schedule(
        action=ScheduleActionStartWorkflow(
            SafeBrowsingRecheckWorkflow.run,
            id=f"{SCHEDULE_ID}-{{{{.ScheduledTime.Unix}}}}",
            task_queue=settings.TEMPORAL_TASK_QUEUE,
        ),
        spec=ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(days=1))],
        ),
        state=ScheduleState(note="Daily Safe Browsing recheck of all stored URLs"),
    )

    try:
        await client.create_schedule(SCHEDULE_ID, schedule)
        logger.info("created schedule %s", SCHEDULE_ID)
    except ScheduleAlreadyRunningError:
        handle = client.get_schedule_handle(SCHEDULE_ID)

        async def _updater(_input: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await handle.update(_updater)
        logger.info("updated existing schedule %s", SCHEDULE_ID)

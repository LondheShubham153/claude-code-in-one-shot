"""Temporal workflows — must be deterministic.

Imports activities through the sandbox per the Python SDK convention.
Time, randomness, and I/O are forbidden in workflow code; we use
`workflow.now()`, `workflow.wait_condition()`, and `workflow.sleep()`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        BatchInput,
        FlushInput,
        LinkRow,
        RecheckInput,
        RecheckResult,
        disable_link,
        flush_click_count,
        list_active_links_batch,
        recheck_url_safety,
    )

# Defaults — can be overridden via workflow input (see ClickCounterParams) for tests.
_DEFAULT_FLUSH_INTERVAL = timedelta(seconds=60)
_DEFAULT_FLUSH_THRESHOLD = 100
_DEFAULT_CONTINUE_AT = 10_000

_FLUSH_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=10,
)
_SAFE_BROWSING_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=3.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=4,
)


@dataclass
class ClickCounterParams:
    slug: str
    flush_interval_seconds: int = 60
    flush_threshold: int = 100
    continue_as_new_at: int = 10_000


@workflow.defn
class ClickCounterWorkflow:
    def __init__(self) -> None:
        self._pending: int = 0
        self._total_signals: int = 0

    @workflow.signal(name="record_click")
    async def record_click(self) -> None:
        self._pending += 1
        self._total_signals += 1

    @workflow.query(name="pending")
    def pending(self) -> int:
        return self._pending

    @workflow.query(name="total_signals")
    def total_signals(self) -> int:
        return self._total_signals

    @workflow.run
    async def run(self, params: ClickCounterParams) -> int:
        # Type annotation required: without it, Temporal's data converter
        # deserializes the JSON arg as a plain dict and the dataclass body
        # below would silently use defaults. Callers must pass
        # ClickCounterParams (see app/temporal/client.py::signal_click).
        flush_interval = timedelta(seconds=params.flush_interval_seconds)
        threshold = params.flush_threshold
        cont_at = params.continue_as_new_at

        while True:
            try:
                await workflow.wait_condition(
                    lambda: self._pending >= threshold,
                    timeout=flush_interval,
                )
            except asyncio.TimeoutError:
                pass  # timer fired — flush whatever is pending (possibly zero)

            if self._pending > 0:
                delta = self._pending
                # Reset BEFORE the activity call: if the activity retries and
                # eventually succeeds, we don't double-count. If it fails
                # permanently after retries, we lose this batch — Temporal
                # retry policy is sized so this is very unlikely.
                self._pending = 0
                await workflow.execute_activity(
                    flush_click_count,
                    FlushInput(slug=params.slug, delta=delta),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=_FLUSH_RETRY,
                )

            if self._total_signals >= cont_at:
                workflow.continue_as_new(args=[params])


@dataclass
class RecheckParams:
    batch_size: int = 500
    concurrency: int = 10


@workflow.defn
class SafeBrowsingRecheckWorkflow:
    @workflow.run
    async def run(self, params: RecheckParams | None = None) -> dict[str, int]:
        params = params or RecheckParams()
        sem = asyncio.Semaphore(params.concurrency)
        offset = 0
        total = 0
        flagged = 0
        disabled = 0

        async def _check_one(row: LinkRow) -> None:
            nonlocal flagged, disabled
            async with sem:
                result: RecheckResult = await workflow.execute_activity(
                    recheck_url_safety,
                    RecheckInput(link_id=row.id, url=row.url),
                    start_to_close_timeout=timedelta(seconds=30),
                    heartbeat_timeout=timedelta(seconds=15),
                    retry_policy=_SAFE_BROWSING_RETRY,
                )
                if result.flagged:
                    flagged += 1
                    changed = await workflow.execute_activity(
                        disable_link,
                        result.link_id,
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=_SAFE_BROWSING_RETRY,
                    )
                    if changed:
                        disabled += 1
                        workflow.logger.info(
                            "disabled link",
                            extra={"link_id": result.link_id, "threat_types": result.threat_types},
                        )

        while True:
            batch: list[LinkRow] = await workflow.execute_activity(
                list_active_links_batch,
                BatchInput(offset=offset, limit=params.batch_size),
                start_to_close_timeout=timedelta(seconds=20),
                retry_policy=_SAFE_BROWSING_RETRY,
            )
            if not batch:
                break
            total += len(batch)
            await asyncio.gather(*(_check_one(row) for row in batch))
            offset += params.batch_size

        workflow.logger.info(
            "recheck complete",
            extra={"checked": total, "flagged": flagged, "disabled": disabled},
        )
        return {"checked": total, "flagged": flagged, "disabled": disabled}

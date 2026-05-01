"""ClickCounterWorkflow tests using time-skipping WorkflowEnvironment.

We mock the flush_click_count activity to record calls without touching DB.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.temporal.activities import FlushInput
from app.temporal.workflows import ClickCounterParams, ClickCounterWorkflow


_recorded_flushes: list[FlushInput] = []


@activity.defn(name="flush_click_count")
async def _mock_flush(payload: FlushInput) -> int:
    _recorded_flushes.append(payload)
    return payload.delta


@pytest.fixture(autouse=True)
def _reset_recorded() -> None:
    _recorded_flushes.clear()


@pytest.mark.asyncio
async def test_threshold_triggers_immediate_flush() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        tq = f"click-{uuid.uuid4()}"
        async with Worker(
            env.client,
            task_queue=tq,
            workflows=[ClickCounterWorkflow],
            activities=[_mock_flush],
        ):
            params = ClickCounterParams(
                slug="abc1234",
                flush_interval_seconds=999,  # essentially disable timer flush
                flush_threshold=5,
                continue_as_new_at=10_000,
            )
            handle = await env.client.start_workflow(
                ClickCounterWorkflow.run,
                params,
                id=f"click-counter:abc1234-{uuid.uuid4()}",
                task_queue=tq,
            )
            for _ in range(5):
                await handle.signal(ClickCounterWorkflow.record_click)

            # Give the workflow a beat to run the activity.
            await asyncio.sleep(0.5)
            assert len(_recorded_flushes) >= 1
            assert _recorded_flushes[0].slug == "abc1234"
            assert _recorded_flushes[0].delta == 5

            await handle.cancel()


@pytest.mark.asyncio
async def test_timer_flush_after_interval() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        tq = f"click-{uuid.uuid4()}"
        async with Worker(
            env.client,
            task_queue=tq,
            workflows=[ClickCounterWorkflow],
            activities=[_mock_flush],
        ):
            params = ClickCounterParams(
                slug="def5678",
                flush_interval_seconds=60,
                flush_threshold=10_000,  # essentially disable threshold flush
                continue_as_new_at=10_000,
            )
            handle = await env.client.start_workflow(
                ClickCounterWorkflow.run,
                params,
                id=f"click-counter:def5678-{uuid.uuid4()}",
                task_queue=tq,
            )
            for _ in range(3):
                await handle.signal(ClickCounterWorkflow.record_click)

            # Time-skip past the flush interval.
            await env.sleep(70)
            await asyncio.sleep(0.3)

            assert any(f.slug == "def5678" and f.delta == 3 for f in _recorded_flushes)
            await handle.cancel()

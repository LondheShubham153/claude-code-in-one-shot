"""SafeBrowsingRecheckWorkflow tests with mocked activities."""

from __future__ import annotations

import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.temporal.activities import (
    BatchInput,
    LinkRow,
    RecheckInput,
    RecheckResult,
)
from app.temporal.workflows import RecheckParams, SafeBrowsingRecheckWorkflow


# Module-level state captured by mock activities
_disabled: list[int] = []


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    _disabled.clear()


@activity.defn(name="list_active_links_batch")
async def _mock_list_batch(payload: BatchInput) -> list[LinkRow]:
    if payload.offset == 0:
        return [
            LinkRow(id=1, url="https://safe1.example/"),
            LinkRow(id=2, url="https://malicious.example/"),
            LinkRow(id=3, url="https://safe2.example/"),
        ]
    return []


@activity.defn(name="recheck_url_safety")
async def _mock_recheck(payload: RecheckInput) -> RecheckResult:
    if "malicious" in payload.url:
        return RecheckResult(
            link_id=payload.link_id, flagged=True, threat_types=["MALWARE"]
        )
    return RecheckResult(link_id=payload.link_id, flagged=False, threat_types=[])


@activity.defn(name="disable_link")
async def _mock_disable(link_id: int) -> bool:
    _disabled.append(link_id)
    return True


@pytest.mark.asyncio
async def test_recheck_disables_flagged_only() -> None:
    async with await WorkflowEnvironment.start_local() as env:
        tq = f"recheck-{uuid.uuid4()}"
        async with Worker(
            env.client,
            task_queue=tq,
            workflows=[SafeBrowsingRecheckWorkflow],
            activities=[_mock_list_batch, _mock_recheck, _mock_disable],
        ):
            result = await env.client.execute_workflow(
                SafeBrowsingRecheckWorkflow.run,
                RecheckParams(batch_size=10, concurrency=2),
                id=f"recheck-{uuid.uuid4()}",
                task_queue=tq,
            )
            assert result["checked"] == 3
            assert result["flagged"] == 1
            assert result["disabled"] == 1
            assert _disabled == [2]

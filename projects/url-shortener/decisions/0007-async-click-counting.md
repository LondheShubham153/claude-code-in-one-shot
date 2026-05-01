# 0007 — Async click counting via Temporal signal

**Status:** Accepted

## Context

Click counts are the single most-written field in the system. The redirect path can't afford a synchronous DB write per click — under load it serializes redirects against DB latency. We need an async, durable, low-latency increment primitive. ADR 0006 explains why we picked Temporal; this ADR explains how the click-counter workflow is shaped.

## Decision

A long-running, per-slug `ClickCounterWorkflow`:

- **Identity**: `workflow_id = f"click-counter:{slug}"`. One workflow per slug. Started lazily on the first click via `start_workflow(..., id_reuse_policy=ALLOW_DUPLICATE_FAILED_ONLY)` (or `signal_with_start` from the redirect endpoint, which is the cleanest API).
- **Signal**: `record_click()` — increments an in-memory counter inside the workflow. The redirect endpoint signals this and returns 302 immediately.
- **Flush trigger** — whichever happens first:
  - 60-second timer (handled via `workflow.wait_condition`)
  - In-memory counter reaches 100 signals
- **Flush activity** — `flush_click_count(slug, n)` runs `UPDATE links SET click_count = click_count + :n WHERE slug = :s`.
- **Continue-as-new** — after every 10,000 signals or 24 hours of wall-clock workflow runtime, the workflow calls `workflow.continue_as_new()` to bound history growth.
- **Sync fallback in the redirect handler** — if `signal_with_start` raises (Temporal unreachable, gRPC error), the handler catches it and falls back to a synchronous `UPDATE click_count = click_count + 1`. Note: a worker-only outage does **not** trigger this path because the signal lands at the Temporal frontend (server-side buffer), not at the worker. Worker-only outages are handled by the durable signal queue and drain on resume.

## Consequences

- **Positive**: Redirect latency is independent of DB latency under normal operation.
- **Positive**: Bursts get batched — 100 clicks in a second flush as one activity instead of 100 row writes.
- **Positive**: Worker outage doesn't lose clicks (signals queue durably in Temporal). DB outage doesn't lose clicks (activity retries until success).
- **Positive**: Temporal's UI shows the per-slug workflow with full history, useful for debugging.
- **Negative**: Eventual consistency. A user submitting the link and immediately checking `click_count` after one click sees 0 until the next flush (≤60s). Acceptable for MVP — `click_count` isn't shown on the redirect itself.
- **Negative**: Delta-based flush is **at-least-once**, not exactly-once. If the activity completes the DB UPDATE but the worker crashes before recording success to Temporal, Temporal retries the activity and we double-add. To make it exactly-once we'd need a per-flush UUID and a dedupe table. Out of MVP scope; documented as a Phase 2 candidate. Practically the over-count is bounded (one flush worth of duplication, ≤100 events) and only happens on activity-level crashes — rare.
- **Negative**: Workflow non-determinism rules apply. `record_click` mutates state, but cannot read system time, randomness, or do I/O. The flush timer uses `workflow.wait_condition` (Temporal's deterministic time primitive), not `asyncio.sleep`. The `temporal-developer` skill enforces this; violations surface as `NonDeterministicWorkflowError` on replay.

## Alternatives considered

- **One workflow for all slugs, with internal per-slug state.** Rejected: a single global workflow becomes a bottleneck and grows unbounded history. Per-slug workflows shard naturally and continue-as-new handles their growth.
- **Per-click workflow** (each click starts a workflow that does one UPDATE and exits). Rejected: ridiculous overhead — you'd run a million workflows for a million clicks. Long-running per-slug with batching is the canonical Temporal pattern for counters.
- **Exact-once via dedupe at flush time** (per-flush UUID + dedupe table) **in MVP**. Rejected because the at-least-once over-count is small and rare; not worth the schema complexity for v1. Phase 2.
- **Flush every 1 second** instead of 60. Rejected: defeats the batching benefit. Tunable via env var if we change our minds.

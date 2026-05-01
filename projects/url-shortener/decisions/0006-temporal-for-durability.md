# 0006 — Temporal for failure-proof execution

**Status:** Accepted

## Context

Two parts of the system are inherently flaky:

1. **Click counting under DB pressure.** `GET /s/{slug}` is the hot path — every redirect issues a write. Under contention (or a brief Postgres outage), a synchronous `UPDATE click_count = click_count + 1` blocks the redirect response.
2. **URL safety changes over time.** A URL that's clean at create time can turn malicious next week (compromised site, expired domain reused for phishing). A one-shot Safe Browsing check at create time is not enough.

The user explicitly asked for a failure-proof system. The right primitive for both problems is durable execution.

## Decision

- **Self-host Temporal** in docker-compose using `temporalio/auto-setup:1.25` with Postgres persistence (reuses the same Postgres instance the app uses, with two extra databases — `temporal` and `temporal_visibility` — created by `scripts/init-temporal-dbs.sql` on first volume init).
- **Python SDK** (`temporalio>=1.7`) — matches the rest of the backend.
- **Worker** runs as a dedicated `worker` service in docker-compose, sharing the backend image but invoked as `python -m app.temporal.worker`.
- **Two workflows** in MVP:
  - `ClickCounterWorkflow` (per-slug, signal-driven, batched flush) — see ADR 0007.
  - `SafeBrowsingRecheckWorkflow` (cron schedule, daily 4am UTC) — fans out one `recheck_url_safety` activity per stored URL with a concurrency semaphore; flagged URLs get `disable_link` (sets `disabled=true`).
- **Schedule registration** is idempotent. `app/temporal/schedules.py::ensure_recheck_schedule()` is called on FastAPI lifespan startup and uses upsert semantics (try `create_schedule`, fall through to `update` on `ScheduleAlreadyRunningError`). Worker restarts don't duplicate schedules.
- **Sync fallback for redirect** — if the Temporal client is unavailable when handling `GET /s/{slug}`, log the error and fall back to a synchronous `UPDATE click_count = click_count + 1`. Click counting degrades gracefully instead of failing.

## Consequences

- **Positive**: Click counting becomes durable. Postgres can be slow, the worker can restart, the network can blip — clicks stay in the workflow's signal queue and flush durably. Redirect latency is independent of DB latency.
- **Positive**: The recheck workflow catches threats that emerge after a link is shortened. This is the strongest reliability win — without it, our system's safety story degrades over time.
- **Positive**: Temporal's UI (at `:8233`) gives ops visibility into what workflows are running, what's stuck, what's retrying. Free observability.
- **Positive**: Activity retry policies handle Google Safe Browsing flake without complicating the application code. The recheck activity retries on 429/5xx with exponential backoff; the workflow doesn't care.
- **Negative**: ~30s cold-start added to `docker compose up` while auto-setup provisions schemas. Subsequent boots are fast.
- **Negative**: Two more services (`temporal`, `temporal-ui`, `worker`) to operate. Acceptable — this is a primary feature, not incidental.
- **Negative**: Workflow code must be deterministic — no `time.now()`, no `random`, no I/O. All side effects move to activities. The `temporal-developer` skill enforces these rules; violations fail loudly via `NonDeterministicWorkflowError`.

## Alternatives considered

- **Inline synchronous click counting** (the obvious approach). Rejected: ties redirect latency to DB latency, fails outright on transient Postgres issues. Documented as the fallback path.
- **Background queue** (Celery, RQ, Arq, BullMQ). Rejected: less observable than Temporal, lacks durable per-key state for the per-slug counter pattern, and the recheck workflow's per-URL retries would need hand-rolled retry orchestration.
- **Cron container running a Python script** for daily rechecks. Rejected: no observability, no built-in retries, and we already have Temporal in the stack for clicks.
- **Temporal Cloud** instead of self-hosted. Rejected for local dev (offline-friendly is nicer); documented as a Phase 3 production target.
- **Async DB writes via `asyncio.create_task`** in the redirect handler. Rejected: lost-on-restart, no retries, no batching.

# URL Shortener

A reliable URL shortener built with FastAPI, React, Postgres, and Temporal. Submit a long URL, get back a short slug; visit `/s/<slug>` for a 302 to the original. Click counts and periodic safety re-checks run as Temporal workflows so flaky external services and DB pressure don't tax the redirect hot path.

## Phase status

- **Phase 1** — MVP: shorten + redirect + click count, three guardrails (URL/SSRF validation, Safe Browsing, rate limit), Temporal workflows for async click counting and daily Safe Browsing re-checks. **Complete — live-verified end-to-end.** Verified scenarios (see [`tasks.md`](./tasks.md) "Validation" section): golden path, all three guardrails (422/400/429), 410 on disabled links, bare `/<slug>` nginx rewrite, schedule registration, **Temporal-outage during shorten still 201** (shorten doesn't depend on Temporal), **worker-outage durability** (signals buffer at Temporal frontend, drain on resume — 5/5 clicks landed). Backend test suite: **57 passing, 82% coverage** (gate 80).
- **Phase 2** — Custom slugs (already supported in schema; not yet exposed on the form), per-link expiry, per-link analytics, auth + per-user dashboard, exact-once click counting via per-flush UUID + dedupe table. _(Deferred)_
- **Phase 3** — Reserved domain, CI/CD, Lighthouse budget, admin view. _(Deferred)_

See [`tasks.md`](./tasks.md) for the granular tracker and [`decisions/`](./decisions/) for ADRs.

## Quickstart

Prereqs: Docker Desktop. Optional: a [Google Safe Browsing API key](https://developers.google.com/safe-browsing/v4/get-started) (without it, safety checks no-op with a warning), an [ngrok auth token](https://dashboard.ngrok.com/get-started/your-authtoken) (only required when going public).

```bash
cp .env.example .env
# edit .env: at minimum POSTGRES_PASSWORD and PUBLIC_BASE_URL

docker compose up --build
```

Then:

- **App**: <http://localhost:8081>
- **Temporal UI**: <http://localhost:8234> — see workflows, activities, schedules
- **API**: <http://localhost:8081/api/links>

To go public over ngrok: `docker compose --profile public up --build`, then read the URL from the ngrok inspector at <http://localhost:4040>. Update `PUBLIC_BASE_URL` in `.env` to the ngrok URL and restart `backend` so new short URLs use the public host.

To stop: `docker compose down`. To wipe the database: `docker compose down -v`.

## Local dev (without Docker)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
# Postgres + Temporal must be reachable; easiest is `docker compose up -d postgres temporal`.
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# Run the worker in a second terminal:
python -m app.temporal.worker
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # Vite at http://localhost:5173, proxies /api and /s to :8000
```

## Running tests

From `projects/url-shortener/backend/` with the venv active:

```bash
pytest                                       # 57 tests, ~5s
pytest -q --cov=app --cov-fail-under=80     # with coverage gate (current: 82%)
pytest tests/test_workflow_click_counter.py  # just the workflow tests
```

Tests use `testcontainers-python` for an ephemeral Postgres per session and `temporalio.testing.WorkflowEnvironment` for workflow tests, so **Docker must be running**. The conftest invokes Alembic via `sys.executable -m alembic` so tests work whether you run `pytest` directly or via `python -m pytest`. `app/temporal/worker.py` is excluded from coverage as a runtime-only entrypoint (see `[tool.coverage.run]` in `pyproject.toml`).

## API

```
POST /api/links                {"url": "https://..."}            → 201 LinkOut
GET  /api/links/{slug}                                           → 200 LinkOut | 404
GET  /s/{slug}                                                   → 302 to original | 404 | 410
GET  /healthz                                                    → 200 (process up)
GET  /readyz                                                     → 200 (DB + Temporal both reachable)
```

`LinkOut` shape:

```json
{
  "slug": "a1B2c3D",
  "url": "https://example.com/some/long/path",
  "short_url": "http://localhost:8081/s/a1B2c3D",
  "click_count": 0,
  "disabled": false,
  "created_at": "2026-05-01T12:00:00Z"
}
```

## How it stays reliable

- **`ClickCounterWorkflow`** — `GET /s/{slug}` signals a per-slug Temporal workflow and returns 302 immediately. The workflow batches and flushes click counts to Postgres every 60s or every 100 signals. Redirect latency is independent of DB latency. Two-layer outage story: if the **worker** is down, signals buffer durably at the Temporal server and drain on resume — no clicks lost, no DB writes during the outage. If **Temporal itself** is unreachable, the redirect handler catches the signaling error and falls back to a synchronous `UPDATE` so click counting still increments.
- **`SafeBrowsingRecheckWorkflow`** — a Temporal cron (4am UTC daily) re-checks every stored URL against Google Safe Browsing. URLs that turn malicious post-creation get `disabled=true` and `/s/{slug}` returns 410 Gone for them.
- **Three guardrails on shorten:**
  1. URL format + scheme allowlist + SSRF block (rejects private/reserved/loopback IPs after DNS resolution, both v4 and v6).
  2. Synchronous Safe Browsing check at create time (env-gated, fail-open on Google flake).
  3. slowapi rate limit (default 10 shortens/IP/min; redirects unlimited).

See [`decisions/0003-guardrails-three-layers.md`](./decisions/0003-guardrails-three-layers.md) and [`decisions/0006-temporal-for-durability.md`](./decisions/0006-temporal-for-durability.md).

## Repo layout

```
.
├── docker-compose.yml          postgres + temporal + temporal-ui + backend + worker + frontend + ngrok
├── scripts/init-temporal-dbs.sql   Bootstraps Temporal's two databases on first volume init
├── backend/
│   ├── pyproject.toml          deps + ruff/mypy/pytest config
│   ├── Dockerfile              multi-stage; runs alembic upgrade head on boot
│   ├── alembic/                migrations 0001 (create) + 0002 (disabled column)
│   ├── app/
│   │   ├── main.py             FastAPI factory + slowapi + lifespan (Temporal client + schedule upsert)
│   │   ├── config.py           pydantic-settings BaseSettings
│   │   ├── db.py               async engine + session
│   │   ├── models.py           SQLAlchemy 2.0 Link
│   │   ├── schemas.py          ShortenRequest / LinkOut
│   │   ├── rate_limit.py       slowapi Limiter w/ XFF-aware key
│   │   ├── routers/            links, redirect, health
│   │   ├── services/           slug, url_validator, safe_browsing
│   │   └── temporal/           client, workflows, activities, worker, schedules
│   └── tests/                  testcontainers Postgres + WorkflowEnvironment
├── frontend/
│   ├── Dockerfile              node20 build → nginx serve
│   ├── nginx/default.conf      SPA fallback + reverse-proxy /api & /s + bare-slug rewrite
│   └── src/                    App, ShortenForm, ResultCard, api.ts, types.ts
├── tasks.md                    Phase-grouped tracker
├── decisions/                  ADR-style decision log (0001–0007)
└── skills-lock.json            Pinned ecosystem skills used to author this project
```

## Notes & gotchas

- **Temporal cold start** — `temporalio/auto-setup` provisions two databases (`temporal`, `temporal_visibility`) and runs schema setup the first time you `docker compose up`. Cold start adds ~30s. Subsequent boots are fast.
- **`PUBLIC_BASE_URL` is encoded in API responses, not slugs** — slugs are the source of truth. If your ngrok URL rotates, regenerate API responses (the frontend does this automatically) but old slugs keep redirecting.
- **Safe Browsing with no API key** — both the synchronous shorten check and the daily recheck workflow no-op with a warning logged once at startup. The app still works; it just doesn't filter malicious URLs.
- **Backend not exposed directly** — `docker-compose.yml` only `expose:`s the backend (no `ports:`). nginx is the only entrypoint. This is what makes `X-Forwarded-For`-based rate limiting trustworthy.
- **`.env` must be gitignored before the first commit.** It is — see [`.gitignore`](./.gitignore).
- **Worker scaling** — single worker is enough for MVP. Increase replicas in `docker-compose.yml` to scale; Temporal handles task distribution. ClickCounterWorkflow is per-slug, so it shards naturally.

## Phase 2 plan (high level)

When ready, ADRs `0008+` will land. Likely additions: per-user dashboards (auth via passkey or OIDC), per-link expiry (`expires_at` column + a per-link timer workflow), structured analytics events (a separate Temporal workflow that fans click signals out into an analytics table), and a Lighthouse budget enforced in CI. None of Phase 1's files are rewritten — Phase 2 is additive.

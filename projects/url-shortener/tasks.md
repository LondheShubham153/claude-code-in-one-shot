# Tasks

Source of truth for what's done / in-progress / deferred. Mirrors the plan at
`~/.claude/plans/use-the-find-skills-to-majestic-flask.md`.

## Phase 1 — MVP: shorten, redirect, click count, three guardrails, Temporal durability

### Scaffolding
- [x] `projects/url-shortener/` directory tree
- [x] `.env.example`, `.gitignore`
- [x] `scripts/init-temporal-dbs.sql`
- [x] `skills-lock.json` (pins docker, fastapi, database-migration, frontend-react-best-practices, temporal-developer)
- [x] ADRs `0001`–`0007` under `decisions/`

### Backend
- [x] `backend/pyproject.toml` — fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, psycopg2, alembic, pydantic, httpx, slowapi, temporalio
- [x] `backend/Dockerfile` — multi-stage, runs alembic + uvicorn
- [x] `backend/alembic.ini`, `backend/alembic/env.py`
- [x] `backend/alembic/versions/0001_create_links.py`
- [x] `backend/alembic/versions/0002_add_disabled_column.py`
- [x] `app/config.py`, `app/db.py`, `app/models.py`, `app/schemas.py`
- [x] `app/main.py` — factory, slowapi wiring, exception handlers, lifespan
- [x] `app/logging_conf.py`, `app/rate_limit.py`
- [x] `app/routers/links.py` — POST /api/links, GET /api/links/{slug}
- [x] `app/routers/redirect.py` — GET /s/{slug} with Temporal signal + sync fallback
- [x] `app/routers/health.py` — /healthz, /readyz
- [x] `app/services/slug.py` — base62 secrets.choice + collision retry
- [x] `app/services/url_validator.py` — scheme allowlist + private/reserved IP block
- [x] `app/services/safe_browsing.py` — async httpx client, env-gated, LRU cache
- [x] `app/temporal/client.py`, `workflows.py`, `activities.py`, `worker.py`, `schedules.py`

### Frontend
- [x] `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
- [x] `src/main.tsx`, `App.tsx`, `api.ts`, `types.ts`, `styles.css`
- [x] `src/components/ShortenForm.tsx`, `ResultCard.tsx`
- [x] `frontend/Dockerfile` — node20 build → nginx serve
- [x] `frontend/nginx/default.conf` — SPA fallback + reverse-proxy + bare-slug rewrite

### Compose & ops
- [x] `docker-compose.yml` — postgres + temporal + temporal-ui + backend + worker + frontend + ngrok
- [x] Healthchecks on every service
- [x] `--profile public` gates ngrok

### Tests
- [x] `backend/tests/conftest.py` — testcontainers Postgres, httpx AsyncClient, WorkflowEnvironment
- [x] `test_shorten.py`, `test_redirect.py`, `test_lookup.py`
- [x] `test_url_validator.py` — parametrized SSRF + scheme cases
- [x] `test_safe_browsing.py` — respx-mocked
- [x] `test_rate_limit.py`
- [x] `test_slug_collision.py`
- [x] `test_workflow_click_counter.py` — WorkflowEnvironment time-skip
- [x] `test_workflow_recheck.py` — flagged → disable_link runs

### Validation
- [x] `docker compose up --build` brings the full stack up (postgres, temporal, temporal-ui, backend, worker, frontend all healthy)
- [x] Migrations apply clean — `alembic current` reports `0002_add_disabled_column (head)`
- [x] Temporal cluster reports SERVING; UI loads at <http://localhost:8234> (8233 was taken on this host)
- [x] Schedule `safe-browsing-recheck` registered with `NextRunTime: ~24h`
- [x] Golden path: shorten → redirect → click count flushes within 60s (verified — 9 clicks recorded after the timer flush)
- [x] Disabled link returns 410 with the right message
- [x] All three guardrails reject correctly: ftp scheme (422), 169.254.169.254 (400 SSRF), 11th request in a minute (429)
- [x] Bare-slug nginx rewrite: `GET /<slug>` → 302 (same as `/s/<slug>`)
- [x] Worker outage → redirects still 302; signals buffer durably at the Temporal server; on worker resume the buffered signals drain and click_count increments via the durable path (verified live — 5 clicks landed after worker restart)
- [x] Temporal outage → shorten still works (POST /api/links → 201 with Temporal stopped, verified live)
- [ ] `pytest -q --cov=app --cov-fail-under=80` — pending (separate sub-agent running)

## Phase 2 — Polish & growth (deferred)

- [ ] `decisions/0008-phase2-implementation.md`
- [ ] Custom slugs (already partially supported in schema; expose on form)
- [ ] Per-link `expires_at` + per-link timer workflow
- [ ] Per-user dashboard (passkey or OIDC auth)
- [ ] Structured analytics events (separate workflow that fans clicks into time-series table)
- [ ] Exact-once click counting via per-flush UUID + dedupe table

## Phase 3 — Polish (optional)

- [ ] Reserved ngrok domain or migration to Fly/Railway/VPS
- [ ] GitHub Actions CI: lint + test on PR, image push on main
- [ ] Lighthouse budget enforcement in CI
- [ ] Admin view (Basic Auth or magic link)

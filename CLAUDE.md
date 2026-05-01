# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository structure

This is a multi-project workspace. Each independent project lives under `projects/<name>/` with its own `Dockerfile`, `docker-compose.yml`, `decisions/` ADRs, `tasks.md`, and (for the url-shortener) its own `skills-lock.json`. Treat each project's directory as the working tree for that project — don't cross-pollute conventions, configs, or dependencies between them unless explicitly aligning.

| Project                         | Stack                                          | Phase 1 status                          | Source of truth                                         |
| ------------------------------- | ---------------------------------------------- | --------------------------------------- | ------------------------------------------------------- |
| `projects/portfolio/`           | Astro static site + nginx + ngrok              | Complete (in-browser verified)          | `projects/portfolio/tasks.md`, `decisions/0001`–`0005`  |
| `projects/url-shortener/`       | FastAPI + React + Postgres + Temporal          | Complete (live-verified end-to-end)     | `projects/url-shortener/tasks.md`, `decisions/0001`–`0007` |

**Repo-root files:** `README.md` (entry point with project links), `CLAUDE.md` (this file), `.claude/settings.local.json` (shared permissions/hooks). Top-level files outside `projects/` like `demo/`, `demo-1.txt` are scratch artifacts from earlier sessions and unrelated to any active project.

## Project: `projects/portfolio/`

Astro static site that auto-renders public repos from the user's GitHub profile. Multi-stage Dockerfile (node build → nginx serve), exposed publicly via an ngrok sidecar.

- **Phase 1 (static site, dockerized, public via ngrok):** complete. Site builds, container stack runs end-to-end, public URL serves the built output, theme toggle verified in browser.
- **Phase 2 (Go backend + Postgres for contact form, cached projects API, analytics):** deferred, not started.
- **Phase 3 (polish — reserved domain, CI, admin view, Lighthouse budget):** optional, not started.

### Common commands (run from `projects/portfolio/`)

- `npm install` — install dependencies (Node ≥20)
- `npm run fetch-github` — pull latest GitHub profile/repo data into `src/data/`
- `npm run build` — produces `dist/` (runs `fetch-github` first via `prebuild`)
- `npm run preview` — serve the built site locally
- `docker compose up --build` — full stack (nginx-served site + ngrok tunnel); requires `NGROK_AUTHTOKEN` in `.env`

## Project: `projects/url-shortener/`

Reliable URL shortener: FastAPI backend, React (Vite + TS) frontend, Postgres 16, self-hosted Temporal (1.25 auto-setup) sharing the same Postgres instance. Reliability primitives are part of the MVP, not a Phase 2 polish.

### Architecture at a glance

- **`ClickCounterWorkflow`** — per-slug Temporal workflow. `GET /s/{slug}` signals it and returns 302 immediately; the workflow batches click counts and flushes to Postgres every 60s or 100 signals. Continue-as-new at 10k events.
- **`SafeBrowsingRecheckWorkflow`** — daily Temporal cron (4am UTC). Re-checks every stored URL against Google Safe Browsing; flagged URLs get `disabled=true` and `/s/{slug}` returns 410 Gone.
- **Three guardrails on shorten** (`POST /api/links`):
  1. URL format + `http`/`https` scheme allowlist + DNS-resolved SSRF block (private/reserved/loopback v4 & v6).
  2. Synchronous Safe Browsing v4 check (env-gated; no-op + warning if `SAFE_BROWSING_API_KEY` unset; fail-open on Google flake).
  3. slowapi per-IP rate limit (`10/minute` default for shorten; redirects unlimited).
- **Two-layer outage story for click counting:**
  - **Worker down** → signals buffer durably at the Temporal frontend, drain on worker resume. No DB writes during the outage; no clicks lost.
  - **Temporal down** → `signal_with_start` raises in the redirect handler; the handler's `except` falls back to a synchronous DB increment. Click counting still works.

### Common commands (run from `projects/url-shortener/`)

- `cp .env.example .env` — first-run setup; at minimum set `POSTGRES_PASSWORD` and `PUBLIC_BASE_URL`
- `docker compose up --build` — full stack: postgres + temporal + temporal-ui + backend + worker + frontend
- `docker compose --profile public up --build` — same plus the ngrok sidecar (requires `NGROK_AUTHTOKEN`)
- `docker compose down` — stop all; `docker compose down -v` also wipes the Postgres volume
- `docker compose run --rm --entrypoint sh backend -c "alembic upgrade head && alembic current"` — apply migrations / show head

### Local development (without Docker)

From `projects/url-shortener/backend/`:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
# Postgres + Temporal must be reachable: `docker compose up -d postgres temporal` from the project root
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# In a second terminal, run the worker:
python -m app.temporal.worker
```

From `projects/url-shortener/frontend/`:

```bash
npm install
npm run dev   # Vite at http://localhost:5173, proxies /api and /s to :8000
```

### Running the test suite (run from `projects/url-shortener/backend/` with `.venv` active)

- `pytest` — full suite
- `pytest -q --cov=app --cov-fail-under=80` — with coverage gate (currently 82%, gate 80)
- Tests use `testcontainers-python` for an ephemeral Postgres per session, and `temporalio.testing.WorkflowEnvironment` for workflow tests. **Docker must be running.** `app/temporal/worker.py` is excluded from coverage as a runtime-only entrypoint.

### Default ports

| Service           | Host port | Notes                                                        |
| ----------------- | --------- | ------------------------------------------------------------ |
| Frontend (nginx)  | `8081`    | `8080` is often taken on dev machines                        |
| Temporal UI       | `8234`    | `8233` is sometimes taken by other Temporal instances        |
| ngrok inspector   | `4040`    | Only active under `--profile public`                         |
| Postgres          | (none)    | Internal only; `docker compose exec postgres psql ...`       |
| Backend           | (none)    | `expose:`d only; nginx is the public entrypoint              |
| Temporal frontend | (none)    | Internal `7233`                                              |

## Authoring conventions (apply to both projects)

- **ADR format**: `decisions/000N-short-title.md`, with `**Status:** Accepted`, then `Context`, `Decision`, `Consequences`, `Alternatives considered`. Mirror the portfolio's `0001-static-stack-astro.md` shape.
- **Phased `tasks.md`**: Phase 1 / 2 / 3 sections; checkboxes (`[x]` done, `[ ]` todo) under sub-headings (Scaffolding, UI, Build, Validation, etc.).
- **Required env vars in compose**: use the `${VAR:?explanatory message}` pattern so `docker compose up` fails loudly on missing values. Use `${VAR:-}` only for truly optional vars (e.g. `SAFE_BROWSING_API_KEY`, `GITHUB_TOKEN`, or anything that's gated behind a `profiles:` declaration).
- **`.env` is always gitignored** before the first commit.
- **Multi-stage Dockerfiles**: builder stage that compiles assets/installs deps, runtime stage that's slim (nginx for static, slim Python for the backend). Add a `HEALTHCHECK` to runtime images.
- **Skills**: pin authoring skills in a `skills-lock.json` at the project root (see `projects/url-shortener/skills-lock.json` for the format).
- **No project-level `.claude/settings.local.json`** — the repo-root one applies to all projects.

## Permissions

Folder creation (`mkdir`) is allowed without confirmation — see `.claude/settings.local.json`. Proceed with directory creation as needed during scaffolding.

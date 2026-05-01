# claude-code-in-one-shot

Multi-project workspace exploring what's buildable in a single Claude Code session, end-to-end. Each project lives under `projects/<name>/` and is independently runnable.

## Projects

### [`projects/portfolio/`](./projects/portfolio/) — Astro portfolio site

A GitHub-driven personal portfolio. Static-built with Astro, served by nginx in a container, exposed publicly via an ngrok sidecar. Phase 1 verified end-to-end in the browser.

- **Stack**: Astro 5 + nginx + ngrok
- **Quickstart**: `cd projects/portfolio && cp .env.example .env && docker compose up --build`
- **Details**: [README](./projects/portfolio/README.md), [tasks](./projects/portfolio/tasks.md), [ADRs 0001–0005](./projects/portfolio/decisions/)

### [`projects/url-shortener/`](./projects/url-shortener/) — Reliable URL shortener with Temporal

FastAPI + React + Postgres + self-hosted Temporal. Click counts and daily Safe Browsing re-checks run as Temporal workflows so flaky external services and DB pressure don't tax the redirect hot path. Three guardrails on shorten: URL format + SSRF block, Google Safe Browsing v4, and per-IP rate limiting.

- **Stack**: Python 3.12 FastAPI + SQLAlchemy[asyncio] + asyncpg + Alembic + slowapi + temporalio; React 18 + Vite + TypeScript; Postgres 16; Temporal 1.25 (auto-setup).
- **Quickstart**: `cd projects/url-shortener && cp .env.example .env && docker compose up --build`, then visit <http://localhost:8081>. Temporal UI at <http://localhost:8234>.
- **Tests**: 57 passing, 82% coverage. From `projects/url-shortener/backend/` with `.venv` active: `pytest -q --cov=app --cov-fail-under=80`.
- **Details**: [README](./projects/url-shortener/README.md), [tasks](./projects/url-shortener/tasks.md), [ADRs 0001–0007](./projects/url-shortener/decisions/)

## Conventions

Each project follows the same shape so navigating between them is predictable:

```
projects/<name>/
├── docker-compose.yml          # full stack with healthchecks
├── Dockerfile (or backend/, frontend/Dockerfile)
├── .env.example                # documented; .env is gitignored
├── README.md                   # quickstart, phase status, gotchas
├── tasks.md                    # phased checkbox tracker
└── decisions/                  # ADR-style architecture decisions (0001–)
```

Authoring conventions, port allocations, and the multi-stage Dockerfile pattern are documented in [`CLAUDE.md`](./CLAUDE.md).

## Working in this repo

- `CLAUDE.md` is the entry point for AI assistants — it captures repo-level guidance, project status, common commands, and conventions both projects follow.
- `.claude/settings.local.json` at the repo root holds shared permissions and hooks. Projects don't have their own.
- The `add-url-shortener` branch added the URL shortener; `main` has the portfolio. Each project is built and verified independently — no inter-project dependencies.

## Status

| Project          | Phase 1                                  | Phase 2                                       | Phase 3                                  |
| ---------------- | ---------------------------------------- | --------------------------------------------- | ---------------------------------------- |
| portfolio        | ✅ complete (in-browser verified)         | deferred — Go backend + Postgres + analytics | optional — domain, CI, admin, Lighthouse |
| url-shortener    | ✅ complete (live-verified end-to-end)    | deferred — auth, expiry, custom slugs, dashboard | optional — domain, CI, Lighthouse        |

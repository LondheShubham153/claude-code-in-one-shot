# 0005 — Phase 2 backend: Go + chi + Postgres

**Status:** Accepted (deferred implementation)

## Context

Phase 2 will add: a contact form, dynamic project sync (cron-refreshed
GitHub data), and visitor analytics. Each needs a backend with a database.
We want to commit to a stack now so the Phase 1 layout reserves space for
it without locking implementation work.

## Decision

- **Language/framework:** Go with [`chi`](https://github.com/go-chi/chi) router.
- **Database:** Postgres 16, accessed via [`pgx`](https://github.com/jackc/pgx).
- **Migrations:** [`golang-migrate`](https://github.com/golang-migrate/migrate)
  with raw SQL files (`*.up.sql` / `*.down.sql`).
- **Layout:** New `backend/` directory at repo root, plugged into the
  existing `docker-compose.yml` as additional services
  (`backend`, `postgres`).
- **Frontend integration:** Astro continues to bake project JSON at build
  time; in Phase 2 it *also* fetches `/api/projects` at runtime when
  available, falling back to the baked JSON if the backend is down. nginx
  gains a `location /api/` reverse-proxy block.

## Consequences

- **Positive**: Single static binary, tiny container image (`scratch` or
  `distroless`), low memory footprint — appropriate for a portfolio backend.
- **Positive**: Go's std-lib HTTP server + chi is sufficient for the three
  endpoints we need; no heavy framework overhead.
- **Positive**: Phase 1 site degrades gracefully if the backend is down.
- **Positive**: ADR captures intent; actual backend code is deferred until
  Phase 2 is requested. No premature implementation.
- **Negative**: Two languages in the repo (TS for frontend, Go for backend).
  Tooling cost is real but small — both have first-class support in
  any modern editor.
- **Negative**: Less universal than Node/Express — onboarding contributors
  may take slightly longer. Acceptable for a personal site.

## Alternatives considered

- **Node.js + Express + Postgres** — Most universal, single language across
  the stack. Rejected because the user prefers Go's deployment story
  (single binary, small image) and is comfortable with Go.
- **Python + FastAPI + Postgres** — Clean async API, automatic OpenAPI
  docs. Rejected for the same reason as Node — Go won on container size
  and deployment simplicity.
- **No commitment, decide in Phase 2** — Risk: Phase 1 layout might not
  reserve appropriate space (e.g., where does `backend/` live, is the
  reverse proxy already considered?). Locking the choice now lets ADR
  0003 and the compose file's structure anticipate it.

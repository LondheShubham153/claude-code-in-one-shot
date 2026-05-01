# 0001 — Stack: FastAPI + React + Postgres

**Status:** Accepted

## Context

We need a URL shortener with reliable APIs (input-validated, rate-limited, malicious-URL-screened), a small UI, and a relational store. The choice of stack should be driven by which ecosystems have well-maintained, high-install agent skills available — the user explicitly asked us to use the right skills rather than freehand code.

## Decision

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + asyncpg.
- **Frontend**: React 18 + Vite + TypeScript.
- **Database**: Postgres 16, run locally via docker-compose.

## Consequences

- **Positive**: Top-tier skills back every layer — `fastapi/fastapi@fastapi` (2K installs, official) and `mindrally/skills@fastapi-python` (8K) for the API; `wshobson/agents@database-migration` (10.6K) for Alembic; `sergiodxa/agent-skills@frontend-react-best-practices` (720) for the UI. The locally-installed `python-library-complete:*` suite already covers testing, security audit, API design, and code quality.
- **Positive**: Pydantic gives us URL parsing, validation, and the SSRF guardrail almost for free (`HttpUrl` + custom validators). FastAPI auto-generates OpenAPI docs at `/docs`.
- **Positive**: Async SQLAlchemy + asyncpg is fast enough for the redirect path; combined with Temporal for click counting, latency stays tight even under contention.
- **Negative**: Two database drivers (`asyncpg` for the app, `psycopg2-binary` for Alembic) — async migrations are still rough. Documented in ADR 0005.
- **Negative**: React for two screens is mild overkill but the skills payoff outweighs the bundle size.

## Alternatives considered

- **Next.js full-stack** — `mindrally/skills@nextjs-react-typescript` (2.4K) covers it. Rejected because the backend skill coverage is weaker for reliability concerns specific to ours (rate limiting, SSRF, Temporal integration), and we wanted a clean process boundary between the API and the worker.
- **Go + chi** — Matches the deferred Phase 2 plan in the portfolio project. No high-quality Go skill on skills.sh, so reliability work would lean on general patterns rather than dedicated skills. Rejected on skill coverage grounds.
- **FastAPI + HTMX** — Simpler than a SPA. Rejected because the user wanted a proper frontend stack, and React's skill coverage is much stronger than HTMX's.

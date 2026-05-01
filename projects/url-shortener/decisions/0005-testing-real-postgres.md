# 0005 — Testing: real Postgres via testcontainers

**Status:** Accepted

## Context

Tests can mock the database, run against SQLite, or run against a real Postgres. We use Postgres-specific features (`INET` type, `TIMESTAMPTZ`, `CHECK (url ~ '^https?://')` regex constraint, `RETURNING` in click-count updates), so SQLite is out. The choice is mock vs real Postgres in CI.

## Decision

- **Real Postgres via `testcontainers-python`.** A session-scoped pytest fixture spins up an ephemeral Postgres 16 container, runs Alembic migrations against it, and yields a connection URL.
- A function-scoped `db_session` fixture wraps each test in a transaction that's rolled back on test exit — gives test isolation without recreating the schema per test.
- **Two database URLs** in env: `DATABASE_URL` for the async app (`postgresql+asyncpg://`) and `ALEMBIC_DATABASE_URL` for migrations (`postgresql+psycopg2://`). Async Alembic is still rough; the sync path is standard.
- **Temporal**: workflow tests use `temporalio.testing.WorkflowEnvironment.start_time_skipping()` — an in-memory time-skipping test server, no container needed. HTTP tests that hit the redirect endpoint monkeypatch the Temporal client to assert `signal_with_start` was called with the right args.
- Safe Browsing: an autouse fixture monkeypatches `safe_browsing.check_url`. Tests targeting the real client opt back in with `respx`.

## Consequences

- **Positive**: Tests catch issues that mock-based suites miss — UNIQUE-constraint violations, INET type coercion, TIMESTAMPTZ rounding, async transaction rollback semantics, CHECK constraint enforcement. The portfolio project's CLAUDE.md captures a related lesson: prior incidents where mock/prod divergence masked real bugs.
- **Positive**: Migrations run on every test session — if a migration is broken, tests fail immediately, not in CI two stages later.
- **Positive**: WorkflowEnvironment time-skipping makes the click-counter test deterministic and fast — no real `sleep(60)` to verify the flush boundary.
- **Negative**: First test run is ~10s slower due to container pull + start. Subsequent runs reuse the image. CI machines benefit from layer caching.
- **Negative**: Tests need Docker available. For developers without Docker, fall back to a `docker-compose.test.yml` profile that brings up `postgres-test` and runs pytest against it.

## Alternatives considered

- **Mock the DB layer entirely** (`unittest.mock` on `db.get_session`). Rejected per the portfolio project's "no mocks" feedback memory — explicit operator preference, with a documented prior incident about mock/prod divergence.
- **SQLite in-memory.** Rejected because of the Postgres-specific features listed above. Maintaining a SQLite-compatible subset is more work than running real Postgres.
- **Embedded `pg_tmp` / `pg_virtualenv`.** Rejected: testcontainers is the de-facto pattern in the Python ecosystem and the database-migration skill leans on it.
- **Real Temporal server in tests** (via testcontainers). Rejected: WorkflowEnvironment is the official path for unit testing workflows; spinning up a full server is ~30s per session and adds zero coverage.

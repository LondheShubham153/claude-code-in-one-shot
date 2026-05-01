# Architecture decision records

Each file captures a non-trivial decision: the context, what was decided, the consequences, and the alternatives considered. Format mirrors the portfolio project's ADRs.

| #    | Title                                  |
| ---- | -------------------------------------- |
| 0001 | Stack: FastAPI + React + Postgres      |
| 0002 | Slug strategy: base62 secrets.choice   |
| 0003 | Three-layer URL guardrails             |
| 0004 | Routing: `/s/{slug}` + nginx rewrite   |
| 0005 | Testing: real Postgres via testcontainers |
| 0006 | Temporal for failure-proof execution   |
| 0007 | Async click counting via signal        |

Add new ADRs with monotonic numbering. Mark superseded ones in their own header (don't delete history).

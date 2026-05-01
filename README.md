# claude-code-in-one-shot

Multi-project workspace exploring what's buildable in a single Claude Code session, end-to-end. Each project lives under `projects/<name>/` and is independently runnable.

This repo is the companion artifact to a Claude Code walkthrough video. The "Concepts covered" section at the bottom maps each chapter to where it shows up in the codebase, so you can use the repo as a study aid alongside the video.

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

## Concepts covered

The companion video walks through 24 Claude Code concepts. The list below preserves the chapter order; the right column points at the concrete artifact in this repo (where one exists) so you can read code alongside the video.

| #  | Concept                              | Where it shows up in this repo                                                                                                                                |
| -- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Introduction to Claude Code          | Both projects — built end-to-end in single Claude Code sessions.                                                                                              |
| 2  | How to install Claude Code           | Prerequisite for running anything in this repo.                                                                                                               |
| 3  | The core loop (how it works)         | Visible in commit history: plan → tool call → result → next step. `git log --oneline` on the `add-url-shortener` branch is one full session captured.         |
| 4  | Permission modes explained           | `.claude/settings.local.json` configures auto-allowed tools (e.g. `mkdir`).                                                                                   |
| 5  | What is CLAUDE.md                    | [`CLAUDE.md`](./CLAUDE.md) at the repo root — entry point for AI assistants, multi-project guidance, conventions.                                             |
| 6  | Auto memory                          | The url-shortener planning session wrote a `feedback_durability_preference.md` memory capturing the user's reliability preference, indexed in `MEMORY.md`.    |
| 7  | Inside the `.claude/` folder         | `.claude/settings.local.json` at the repo root — shared permissions and hooks for both projects.                                                              |
| 8  | Configuring `settings.json`          | Same file. No project-level overrides; the repo-root config applies to both projects (documented in [`CLAUDE.md`](./CLAUDE.md)).                              |
| 9  | Slash commands                       | The url-shortener planning session used `/plan`, `/find-skills`, `/temporal-developer`. Each maps to a skill or built-in command.                             |
| 10 | What are skills                      | [`projects/url-shortener/skills-lock.json`](./projects/url-shortener/skills-lock.json) pins five skills (docker, fastapi, database-migration, frontend-react-best-practices, temporal-developer). The portfolio uses `github-issues`. |
| 11 | What are subagents                   | The url-shortener was built using `Explore` (research), `Plan` (design), and `general-purpose` (test/verify/push). The verify+test+push handoff at end of session ran three sub-agents in parallel-then-sequential. |
| 12 | What are hooks                       | A `code-reviewer` hook is configured in `.claude/settings.local.json`.                                                                                        |
| 13 | What is MCP                          | The session had GitHub MCP tools available (`mcp__github__*`) and IDE diagnostics (`mcp__ide__getDiagnostics`).                                               |
| 14 | Plugins and marketplaces             | `npx skills find <query>` was used to discover skills from skills.sh; pinning is via `skills-lock.json` (see #10).                                            |
| 15 | IDE integrations and surfaces        | VS Code-style file selection signals (system reminders when the user opens a file) drove a couple of mid-session course corrections.                          |
| 16 | Headless mode and Agent SDK          | Sub-agents (#11) run via the Agent SDK shape under the hood — the parallel test+verify+push handoff is a small live demo.                                     |
| 17 | What are routines                    | `/schedule` skill is available; mentioned in the closing offer pattern after shipping work that has a natural follow-up.                                      |
| 18 | What are checkpoints                 | The url-shortener plan was written to `~/.claude/plans/<...>.md` and approved via `ExitPlanMode` — that file is the durable session checkpoint.               |
| 19 | Output styles                        | Concise update style throughout — short status lines, end-of-turn one-or-two-sentence summaries.                                                              |
| 20 | Hidden gems and power moves          | `signal_with_start` for the per-slug Temporal workflow is a Temporal "power move" — see [`backend/app/temporal/client.py`](./projects/url-shortener/backend/app/temporal/client.py) and [ADR 0007](./projects/url-shortener/decisions/0007-async-click-counting.md). The parallel-then-gated sub-agent handoff is a Claude Code "power move." |
| 21 | Pro patterns                         | Plan mode → AskUserQuestion → ExitPlanMode → execute, used to scope the url-shortener before writing a line of code. ADRs capture every non-trivial decision. Two-layer outage story (worker-down vs Temporal-down) documented in [ADR 0006](./projects/url-shortener/decisions/0006-temporal-for-durability.md). |
| 22 | Troubleshooting                      | Live verification surfaced real issues that got fixed in-session: nginx PCRE2 regex, host port conflicts on `:8080`/`:8233`, schedule update API misuse, missing type annotation breaking Temporal data conversion. All fixed and documented in commit messages on the `add-url-shortener` branch. |
| 23 | Cheat sheet recap                    | This table is the cheat sheet — concept → file/path → ADR.                                                                                                    |
| 24 | Outro and Projects                   | The two projects in [`projects/`](./projects/) are the deliverables: a static portfolio and a reliable URL shortener with Temporal-backed click counting and daily safety re-checks.                            |

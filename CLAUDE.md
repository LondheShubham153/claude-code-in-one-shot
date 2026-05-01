# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

The active project lives at `projects/portfolio/` — an Astro static site that renders a GitHub-driven portfolio, served by nginx in a container, exposed publicly via an ngrok sidecar.

**Phase 1 (static site, dockerized, public via ngrok):** complete. Site builds, container stack runs end-to-end, public URL serves the built output, theme toggle verified in browser.

**Phase 2 (Go backend + Postgres for contact form, cached projects API, analytics):** deferred, not started.

**Phase 3 (polish — reserved domain, CI, admin view, Lighthouse budget):** optional, not started.

Source of truth for task state: `projects/portfolio/tasks.md`. Architecture decisions: `projects/portfolio/decisions/0001`–`0005`.

Top-level files outside `projects/` (`demo/`, `demo-1.txt`) are scratch artifacts from earlier sessions and unrelated to the portfolio project.

## Common commands (run from `projects/portfolio/`)

- `npm install` — install dependencies (Node ≥20)
- `npm run fetch-github` — pull latest GitHub profile/repo data into `src/data/`
- `npm run build` — produces `dist/` (runs `fetch-github` first via `prebuild`)
- `npm run preview` — serve the built site locally
- `docker compose up --build` — full stack (nginx-served site + ngrok tunnel); requires `NGROK_AUTHTOKEN` in `.env`

## Permissions

Folder creation (`mkdir`) is allowed without confirmation — see `.claude/settings.local.json`. Proceed with directory creation as needed during scaffolding.

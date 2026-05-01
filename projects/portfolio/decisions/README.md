# Architecture Decision Records (ADRs)

This directory captures architectural decisions made during the project. Each
ADR is a short, immutable record of *why* a particular choice was made — so a
future contributor (or future-you) can reconstruct the reasoning without
re-litigating the discussion.

## Format

Each ADR is one markdown file, named `NNNN-kebab-case-title.md`, containing:

- **Status** — one of: Accepted, Superseded by NNNN, Deprecated.
- **Context** — what's the problem? What constraints exist?
- **Decision** — what did we choose?
- **Consequences** — what does this enable, and what trade-offs come with it?
- **Alternatives considered** — what else was on the table, and why was it rejected?

ADRs are written *once* and not edited. If a decision is revisited, write a
new ADR and mark the old one "Superseded by NNNN".

## Index

| # | Title | Status |
|---|---|---|
| 0001 | [Static stack: Astro](./0001-static-stack-astro.md) | Accepted |
| 0002 | [GitHub data: build-time fetch](./0002-github-build-time-fetch.md) | Accepted |
| 0003 | [Hosting: nginx in Docker, public via ngrok](./0003-nginx-docker-compose-ngrok.md) | Accepted |
| 0004 | [Theming: dark + light toggle, no FOUC](./0004-theme-dark-light-toggle.md) | Accepted |
| 0005 | [Phase 2 backend stack: Go + chi + Postgres](./0005-phase2-backend-go-chi-postgres.md) | Accepted (deferred implementation) |

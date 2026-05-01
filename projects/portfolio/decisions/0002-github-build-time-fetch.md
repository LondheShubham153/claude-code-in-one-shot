# 0002 — GitHub data: build-time fetch

**Status:** Accepted

## Context

The site shows the user's profile + public repos from
`github.com/LondheShubham153`. There's no backend in Phase 1, so the data
has to land in the browser somehow. Options sit on a spectrum from "bake
into image" to "fetch live from the browser".

## Decision

Fetch GitHub data **at build time** via `scripts/fetch-github.mjs`, wired as
`prebuild` (and `predev`) in `package.json`. The script writes
`src/data/profile.json` and `src/data/projects.json`, which Astro components
import directly. No runtime API calls from the browser.

## Consequences

- **Positive**: Zero runtime API dependency. Page loads are pure static
  files. No CORS, no rate-limit-induced failures during normal browsing.
- **Positive**: The Docker image is self-contained and reproducible —
  `docker compose up --build` produces a fully populated site.
- **Positive**: Freshness is opt-in (`docker compose up --build` re-fetches),
  which matches user expectations for a portfolio rather than a feed.
- **Negative**: Star counts / new repos require a rebuild to show up. Phase 2
  switches `GET /api/projects` to a backend cache refreshed by an in-process
  ticker, eliminating this constraint without rewriting Phase 1 logic.
- **Negative**: Unauthenticated GitHub API allows only 60 req/hr/IP. During
  iterative `docker build` cycles this can rate-limit. Mitigated via
  optional `GITHUB_TOKEN` build-arg (5000/hr authenticated).

## Alternatives considered

- **Client-side fetch at runtime** — Always-fresh data without rebuilds.
  Rejected because (a) unauthenticated calls are 60/hr/IP — a single user
  refreshing repeatedly can exhaust the quota, and (b) it leaks GitHub-API
  call latency into first paint.
- **Pinned-repos-only build-time fetch** — Curate via the GitHub profile
  pinned set. Rejected as too restrictive for now; we want all non-fork
  non-archived repos sorted by stars. Easy to switch later by changing the
  filter in `fetch-github.mjs`.
- **Manually curated `projects.json`** — Most control, no API dependency.
  Rejected because it requires manual upkeep — exactly the kind of friction
  a portfolio site should not have.

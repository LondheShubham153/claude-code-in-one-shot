# 0004 — Routing: `/s/{slug}` + nginx rewrite

**Status:** Accepted

## Context

The natural URL form for a shortener is `https://host/<slug>` — bare path, no prefix. But our app also has `/api/...`, `/healthz`, `/readyz`, plus the Vite/React frontend at `/` (index, assets). A FastAPI catch-all on `/{slug}` would shadow all of those.

## Decision

- **FastAPI** registers redirects at `/s/{slug}`, with explicit constraints (`{slug:str}` and a regex validator).
- **nginx** rewrites bare paths matching `^/[A-Za-z0-9_-]{4,32}$` to `/s/<slug>` before reverse-proxying to the backend.
- Reserved-word denylist (`api`, `healthz`, `readyz`, `s`, `admin`, `www`) is enforced at slug creation time so the rewrite can never match a route the frontend wants.

## Consequences

- **Positive**: Public-facing URLs stay short — users see `https://host/a1B2c3D` even though FastAPI serves it from `/s/a1B2c3D`.
- **Positive**: No risk of slug routes shadowing API routes, regardless of slug length or alphabet. The denylist is the safety net.
- **Positive**: Direct hits to `/s/{slug}` still work (e.g. for testing without nginx in front).
- **Negative**: Two places to keep in sync — the slug regex in `app/schemas.py` and the nginx rewrite regex. We document this in `frontend/nginx/default.conf` and in `app/services/slug.py` so any change touches both.
- **Negative**: nginx config is slightly more complex than a flat reverse proxy. The added rewrite is one `if` block.

## Alternatives considered

- **All slugs under `/s/`** (no rewrite). Rejected: defeats the "short" in URL shortener — `https://host/s/a1B2c3D` is two characters longer than necessary on every share.
- **Catch-all in FastAPI with priority ordering** (`/api/...` and `/healthz` registered first, then `/{slug:str}` last). Rejected: works but is fragile — adding any new top-level route risks colliding with an existing slug. The reserved-word denylist alone isn't enough because slugs are auto-generated and could in theory match a future route name.
- **Subdomain split** (`s.host` for redirects, `app.host` for the API and UI). Rejected for MVP — too much DNS plumbing for negligible benefit at this scale; nice-to-have for Phase 3.

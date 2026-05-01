# 0003 — Hosting: nginx in Docker, public via ngrok

**Status:** Accepted

## Context

Phase 1 needs to be runnable locally and reachable from the public internet
without renting a server, buying a domain, or going through a cloud
deployment workflow. The user explicitly chose nginx + Docker + ngrok.

## Decision

Two-service `docker-compose.yml`:

- **`web`** — multi-stage build (Node 20 builder → nginx 1.27-alpine
  runtime). nginx serves the built `dist/` from Astro.
- **`ngrok`** — official `ngrok/ngrok:latest` image, started as a sidecar,
  tunneling `web:80`. Reads `NGROK_AUTHTOKEN` from `.env`. Inspector
  dashboard exposed on host port 4040.

`docker compose up --build` brings both up; `docker compose down` tears them
down.

## Consequences

- **Positive**: Single command to a public URL. No external infrastructure.
- **Positive**: nginx handles gzip, caching headers, and the `index.html`
  fallback — standard, well-understood.
- **Positive**: Multi-stage Dockerfile keeps the runtime image small (~20MB
  for `nginx:alpine` + the static `dist/`).
- **Negative**: ngrok free-tier URLs are ephemeral — every restart gets a
  new public URL. Acceptable for Phase 1; addressed in Phase 3 (reserved
  domain or migration off ngrok).
- **Negative**: ngrok inspector dashboard at `:4040` is bound to host. Fine
  for local dev; if the host is ever multi-tenant, that's an exposure to be
  aware of.
- **Negative**: `docker compose up` requires `NGROK_AUTHTOKEN` set. The
  compose file uses `${NGROK_AUTHTOKEN:?…}` so the failure mode is a clear
  error message rather than a confusing tunnel-startup failure.

## Alternatives considered

- **Run ngrok manually outside Docker** — Simpler container, but two
  terminals and an extra setup step for every run. Rejected for ergonomics.
- **Cloudflare Tunnel** — Comparable feature set, would also work. Rejected
  because the user explicitly named ngrok and the configuration overhead is
  similar.
- **Skip the tunnel entirely (localhost only)** — Doesn't meet the "public"
  requirement.

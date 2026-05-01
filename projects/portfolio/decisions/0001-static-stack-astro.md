# 0001 — Static stack: Astro

**Status:** Accepted

## Context

We need a portfolio site that:

1. Renders mostly static content (projects from GitHub, About, Contact).
2. Phase 1 has no backend; Phase 2 adds a Go API. We want the static→dynamic
   transition to be additive, not a rewrite.
3. Loads fast and ships small JS payloads (no SPA framework if avoidable).

## Decision

Use **Astro** (v5+) with `output: "static"`.

## Consequences

- **Positive**: Component model (`.astro` files) is familiar to anyone who
  knows JSX. Astro ships zero JS by default and only hydrates components
  marked `client:*` — perfect for a near-static portfolio. When Phase 2 adds
  a backend, we can flip individual pages to SSR or add API routes without
  abandoning the framework.
- **Positive**: Native TypeScript, Vite-powered HMR, Markdown/MDX support if
  we ever want a `/blog`.
- **Negative**: Adds a Node build step (vs. plain HTML). Mitigated by the
  multi-stage Dockerfile — the runtime image only contains nginx + `dist/`.
- **Negative**: Slightly heavier toolchain than Eleventy/Hugo for what is
  essentially one page today.

## Alternatives considered

- **Plain HTML/CSS/JS** — Simplest possible. Rejected because Phase 2 would
  require either a separate frontend or a manual rewrite when we want
  components, theme handling, or future routing. The phase-evolution story
  is the deciding factor.
- **Next.js (static export)** — Smooth path to Next API routes in Phase 2.
  Rejected because we picked Go for the backend (ADR 0005), so Next's
  full-stack story is wasted weight; React + Next is heavier than needed for
  a portfolio.
- **Eleventy / Hugo** — Mature, minimal SSGs. Rejected because Astro's
  component model evolves better as the site grows past one page, and
  TypeScript support is first-class.

# Tasks

Source of truth for what's done / in-progress / deferred. Mirrors the plan at
`~/.claude/plans/lets-plan-for-a-snuggly-music.md`.

## Phase 1 — Static site, dockerized, public via ngrok

### Scaffolding
- [x] `projects/portfolio/` directory tree
- [x] Astro `package.json`, `astro.config.mjs`, `tsconfig.json`
- [x] Placeholder `src/data/{profile,projects}.json`

### UI
- [x] `BaseLayout.astro` with FOUC-free theme bootstrap
- [x] `ThemeToggle.astro` — dark/light switcher with `localStorage` persistence
- [x] `Hero.astro` — name + avatar + bio from GitHub profile
- [x] `About.astro` — company + location + repo/follower counts
- [x] `ProjectCard.astro` — single repo card (stars, forks, language, topics)
- [x] `ProjectGrid.astro` — auto-fill grid of cards
- [x] `ContactPlaceholder.astro` — static links (replaced by form in Phase 2)
- [x] `src/styles/global.css` — light/dark CSS variables
- [x] `src/pages/index.astro` — single-page composition

### Build & deploy
- [x] `scripts/fetch-github.mjs` — build-time GitHub API fetcher
- [x] Multi-stage `Dockerfile` (node build → nginx serve)
- [x] `nginx/default.conf` (gzip, caching, fallback)
- [x] `docker-compose.yml` (web + ngrok sidecar)
- [x] `.env.example`, `.gitignore`

### Docs & decisions
- [x] `README.md` quickstart
- [x] `tasks.md` (this file)
- [x] ADRs `0001`–`0005` under `decisions/`

### Validation
- [x] `npm install` succeeds (277 packages, ~1m)
- [x] `npm run fetch-github` returns real data — 183 public repos, 74 kept after filter
- [x] `npm run build` produces a `dist/` (1 page, 328ms)
- [x] `npm run preview` serves the page (HTTP 200, 47KB) with all 74 project cards rendered
- [x] `docker compose up --build` brings both services up
- [x] ngrok public URL serves the built site end-to-end
- [x] Theme toggle flips dark↔light, persists across reload, no FOUC

**Phase 1 complete.**

## Phase 2 — Go backend + Postgres (deferred)

- [ ] `decisions/0006-phase2-implementation.md` capturing then-current trade-offs
- [ ] Scaffold `backend/` (Go module, chi router, pgx)
- [ ] `backend/Dockerfile` (multi-stage builder → distroless/scratch)
- [ ] Extend `docker-compose.yml` with `backend` + `postgres` services
- [ ] Migrations setup (`golang-migrate`, `migrations/0001_init.up.sql`)
- [ ] `POST /api/contact` (validate, persist; email forwarder optional)
- [ ] `GET /api/projects` (cached GitHub data, in-process refresh ticker)
- [ ] `POST /api/analytics/pageview` (path, ts, ua_hash, ip_hash)
- [ ] Astro: swap `ContactPlaceholder` for `ContactForm` posting to `/api/contact`
- [ ] Astro: pageview beacon embedded in `BaseLayout`
- [ ] nginx: reverse-proxy `location /api/` to backend service
- [ ] End-to-end validation: full stack via `docker compose up`

## Phase 3 — Polish (optional)

- [ ] Reserved ngrok domain or migration to Fly/Railway/VPS
- [ ] GitHub Actions CI: lint + build on PR, deploy on main
- [ ] Admin view for analytics (Basic Auth or magic link)
- [ ] Lighthouse budget enforcement in CI

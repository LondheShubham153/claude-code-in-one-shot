# Portfolio

Personal portfolio site that auto-showcases public repos from
[`@LondheShubham153`](https://github.com/LondheShubham153). Static-built with
Astro, served by nginx in a Docker container, exposed publicly via ngrok.

## Phase status

- **Phase 1** — Static site, dockerized, public via ngrok. _(In progress)_
- **Phase 2** — Go + chi backend, Postgres, contact form, dynamic project sync, analytics. _(Deferred)_
- **Phase 3** — Reserved domain, CI/CD, admin dashboard, Lighthouse budget. _(Deferred)_

See [`tasks.md`](./tasks.md) for the granular task tracker and
[`decisions/`](./decisions/) for ADRs explaining each architectural choice.

## Quickstart (Phase 1)

Prereqs: Docker Desktop, an [ngrok auth token](https://dashboard.ngrok.com/get-started/your-authtoken).

```bash
cp .env.example .env
# edit .env: fill in NGROK_AUTHTOKEN (required) and GITHUB_TOKEN (optional)

docker compose up --build
```

Then:

- **Local inspector**: <http://localhost:4040> — ngrok dashboard, shows the public URL.
- **Public URL**: printed in `ngrok` logs, like `https://<random>.ngrok-free.app`.

To stop: `docker compose down`.

## Local dev (without Docker)

```bash
npm install
npm run dev   # implicitly runs scripts/fetch-github.mjs first via predev
```

Astro dev server runs at <http://localhost:4321>.

## How it stays up to date

Every `docker compose up --build` re-runs `scripts/fetch-github.mjs` (wired as
`prebuild`), so star counts, new repos, and bio changes pick up automatically
on rebuild. No backend, no cron — just rebuild the image to refresh.

## Repo layout

```
.
├── astro.config.mjs       Astro config (static output)
├── package.json           Scripts: dev, build (with prebuild fetch), fetch-github
├── scripts/
│   └── fetch-github.mjs   Build-time GitHub fetcher
├── src/
│   ├── data/              Generated JSON (overwritten by fetcher)
│   ├── layouts/           Page shell + theme bootstrap
│   ├── components/        Hero, About, ProjectGrid, ContactPlaceholder, ThemeToggle
│   ├── pages/index.astro  Single-page composition
│   └── styles/global.css  Shared styles + theme variables
├── nginx/default.conf     gzip, caching, MIME, fallback
├── Dockerfile             Multi-stage: node build → nginx serve
├── docker-compose.yml     web + ngrok services
├── tasks.md               Phase-grouped task tracker
└── decisions/             ADR-style decision log
```

## Notes & gotchas

- **GitHub rate limits** — unauthenticated `docker compose up --build` can fail
  if you've been iterating. Set `GITHUB_TOKEN` in `.env` to raise the limit
  from 60/hr to 5000/hr. The token only needs `public_repo` read scope.
- **ngrok URLs are ephemeral** on the free tier — every restart gets a new
  public URL. A reserved domain or migrating off ngrok is a Phase 3 concern.
- **Theme toggle** — uses `prefers-color-scheme` for first paint and stores
  the user's choice in `localStorage`. The bootstrap script is inline in
  `<head>` to prevent flash-of-incorrect-theme.
- **About copy** — pulled from your GitHub profile (`bio`, `company`,
  `location`). To update: edit your GitHub profile, rebuild.

## Phase 2 plan (high level)

When ready, `decisions/0006-phase2-implementation.md` will be added at start.
The Go service plugs in additively: new `backend/` directory, new compose
services (`backend`, `postgres`), nginx gains a `location /api/` block, and
the existing static site gracefully degrades to Phase-1 behavior if the
backend is down. No Phase-1 file is rewritten.

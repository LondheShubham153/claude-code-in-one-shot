# claude-code-in-one-shot

Projects built end-to-end with [Claude Code](https://claude.ai/code) in a single session — scaffolded, dockerized, deployed, and documented from one prompt-driven flow.

## Projects

| Project | Stack | Status |
|---|---|---|
| [`projects/portfolio/`](projects/portfolio/) | Astro static site + nginx + ngrok, GitHub-driven | Phase 1 complete |

Additional one-shot projects (backend, URL shortener, pastebin, CLI todo, Temporal demo, Claude API chatbot) are tracked in [issue #1](https://github.com/LondheShubham153/claude-code-in-one-shot/issues/1).

## Repo conventions

Each project under `projects/<name>/` follows the same shape:

- `README.md` — what it is, how to run it locally
- `tasks.md` — source of truth for task state
- `decisions/` — numbered ADRs (`0001-*.md`, `0002-*.md`, …)

The root [`CLAUDE.md`](CLAUDE.md) routes Claude Code into the active project and lists common commands.

## Quickstart (portfolio)

Requires Node ≥20, Docker, and an `NGROK_AUTHTOKEN` for the public tunnel.

```bash
cd projects/portfolio
npm install
npm run build              # produces dist/
docker compose up --build  # nginx-served site + ngrok sidecar
```

See [`projects/portfolio/README.md`](projects/portfolio/README.md) for the full setup, environment variables, and architecture notes.

## `.claude/` setup

Each project ships its own `.claude/` directory with:

- a `code-reviewer` subagent that runs on file changes
- `PostToolUse` / `FileChanged` hooks wired in `.claude/settings.local.json`

This pattern is reusable across projects — copy the directory into a new project and adjust the agent prompts.

## Contributing

Fork, swap in your own GitHub username (used by the portfolio's GitHub-driven content), and follow the project's README. See issue #1 for the documentation backlog and proposed projects.

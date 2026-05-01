# 0004 — Theming: dark + light toggle, no FOUC

**Status:** Accepted

## Context

The user wants a dark+light theme with a working toggle. The hard part is
avoiding flash-of-incorrect-theme (FOIT/FOUC): if the theme is applied
client-side after React/JS hydration, the user sees a brief flash of the
wrong theme on first paint. That looks broken.

## Decision

- A small **inline `<script is:inline>`** in `BaseLayout.astro` `<head>`
  reads `localStorage.theme` and `prefers-color-scheme`, then sets
  `data-theme="light"|"dark"` on `<html>` *before* paint.
- All theme-dependent styling lives in CSS variables under `:root` and
  `[data-theme="dark"]` selectors in `global.css`.
- A separate `ThemeToggle.astro` component renders a fixed-position button
  with a small client script that flips `data-theme` and writes to
  `localStorage`.

## Consequences

- **Positive**: Zero flash on first paint, even with full SSG/static
  output.
- **Positive**: Respects OS preference for first-time visitors.
- **Positive**: User's choice persists across visits (localStorage).
- **Positive**: All styling driven by CSS variables, so adding new
  components doesn't require touching theme logic.
- **Negative**: Inline `<script>` runs on every page (cheap, but it's there).
- **Negative**: Disabling JavaScript breaks the toggle but not the page —
  users still get a usable site at the OS-preferred theme.

## Alternatives considered

- **CSS-only via `prefers-color-scheme`** — No JS, no toggle, just respect
  the OS. Rejected because the user wants an explicit toggle.
- **Astro/React state hook for theme** — Would require client hydration,
  which is exactly what causes FOUC. Rejected.
- **Save preference in a cookie + SSR** — Would also work but requires SSR,
  and Phase 1 is fully static. Premature.

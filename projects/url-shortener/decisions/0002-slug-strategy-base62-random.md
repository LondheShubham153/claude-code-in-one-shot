# 0002 — Slug strategy: base62 from `secrets.choice`

**Status:** Accepted

## Context

Every shortened URL needs a unique slug. The choice space drives collision probability, the alphabet drives URL aesthetics, and the generator drives whether slugs are predictable (and therefore enumeration-scrapable).

## Decision

- **Length**: 7 characters.
- **Alphabet**: base62 — `[A-Za-z0-9]`.
- **Generator**: `''.join(secrets.choice(ALPHABET) for _ in range(length))`.
- **Collision handling**: catch `IntegrityError` on the UNIQUE constraint, rollback, regenerate, retry up to 5 times. Retries 6–10 bump the length by 1 as a defense-in-depth measure. After 10 total failures: surface 500.
- **Custom slugs**: schema supports them (`custom_slug` field, regex-validated, reserved-word denylist), but Phase 1 doesn't expose them on the form. Phase 2 will.

## Consequences

- **Positive**: 62⁷ ≈ 3.5 trillion. At 1M live links, the birthday-bound collision probability per insert is around 10⁻⁶. The retry loop handles the rest.
- **Positive**: `secrets.choice` is cryptographically random — slugs aren't predictable, so attackers can't enumerate the URL space to harvest others' links.
- **Positive**: Base62 keeps URLs short and avoids ambiguous characters with care (no spaces, no punctuation that needs escaping). We accepted ambiguous pairs (`O`/`0`, `l`/`1`) for simplicity — the QR-code use case isn't on the roadmap.
- **Negative**: 7 characters is one more than YouTube's 11-char IDs (which use a 64-character alphabet plus dashes/underscores) — slightly less compact. Acceptable.

## Alternatives considered

- **Sequential IDs** (e.g. base62-encode the row id). Rejected: leaks creation order and allows enumeration.
- **Hash of URL** (truncated SHA-256). Rejected: same URL → same slug (unwanted: two users shortening the same URL should get distinct slugs for distinct analytics), and deterministic slugs are even more enumeration-friendly than sequential.
- **`uuid4().hex[:7]`** — fine but uses only `[0-9a-f]`, much smaller alphabet (16⁷ ≈ 268M, three orders of magnitude tighter). Rejected.
- **8 or 10 characters** for extra headroom. Rejected: 7 is plenty at MVP scale, and longer slugs are uglier in shared links.

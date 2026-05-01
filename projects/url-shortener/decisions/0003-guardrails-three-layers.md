# 0003 — Three-layer URL guardrails

**Status:** Accepted

## Context

URL shorteners are high-value abuse targets: malware distribution, phishing, SSRF reconnaissance, denial-of-service against the shortener itself. The user explicitly asked for guardrails, and listed three concerns: input validation (URL format and SSRF), malicious-URL filtering, and rate limiting per IP.

## Decision

Three layers, all of them on by default.

### Layer 1 — URL format + scheme allowlist + SSRF block (`app/services/url_validator.py`)

- Pydantic `HttpUrl` enforces that the input parses as a URL.
- `ALLOWED_SCHEMES = ["http", "https"]`. `javascript:`, `data:`, `file:`, `ftp:`, etc. are rejected at parse time.
- After parsing, resolve the host with `socket.getaddrinfo`. Reject the URL if **any** resolved address satisfies `is_private | is_loopback | is_link_local | is_reserved | is_multicast`. This covers IPv4 (`127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254.169.254`, etc.) and IPv6 (`[::1]`, `fe80::/10`, `fc00::/7`).
- Maximum URL length: 2048 characters.

### Layer 2 — Google Safe Browsing v4 (`app/services/safe_browsing.py`)

- Synchronous check at shorten time: POST to `safebrowsing.googleapis.com/v4/threatMatches:find` with the four threat types (MALWARE, SOCIAL_ENGINEERING, UNWANTED_SOFTWARE, POTENTIALLY_HARMFUL_APPLICATION).
- Daily Temporal cron workflow re-checks every stored URL. URLs that turn malicious post-creation get `disabled=true`; `/s/{slug}` returns 410 Gone for them. See ADR 0006.
- **Env-gated**: if `SAFE_BROWSING_API_KEY` is unset, both checks no-op with a single warning logged at startup. The app still works without an API key — it just doesn't filter malicious URLs.
- **Fail-open** on Google network/HTTP errors at shorten time: log + metric, but accept the link. Don't block legit users on Google flake. The recheck workflow will catch it the next day if Google was wrong.
- LRU cache (1h TTL) for negative results — the same URL submitted twice in quick succession hits cache.

### Layer 3 — Per-IP rate limit (`app/rate_limit.py`)

- `slowapi.Limiter(key_func=get_real_ip)` where `get_real_ip` reads the first IP from `X-Forwarded-For` (since nginx is in front).
- `POST /api/links` decorated with `@limiter.limit(settings.RATE_LIMIT_SHORTEN)` — default `10/minute`.
- Redirects (`GET /s/{slug}`), lookups, and health checks are **not** rate-limited.
- 11th request in a minute returns `429 Too Many Requests` with a `Retry-After` header.

## Consequences

- **Positive**: All three layers are deterministic and easy to test. The parametrized SSRF test set covers IPv4, IPv6, link-local, multicast, and DNS-resolved private IPs.
- **Positive**: Each layer fails closed (validation rejects on doubt) except the Safe Browsing layer at create time (fail-open). The fail-open is the right trade — Google goes down, we keep working, and the next day's recheck will retroactively disable bad links.
- **Positive**: `X-Forwarded-For` spoofing is the obvious concern with header-based rate limiting. We mitigate by **not exposing the backend port** in docker-compose (`expose:` only, no `ports:`), so only nginx can reach it. Direct backend access requires getting onto the docker network.
- **Negative**: DNS rebinding could in theory bypass the SSRF check (validation lookup returns public IP, redirect-time lookup returns private IP). We never fetch the URL server-side at redirect time — we 302 — so the attack surface is mostly limited to "user clicks a link that resolves to their own private network." That's no worse than them typing the URL directly. Documented as accepted risk.
- **Negative**: Google's free Safe Browsing tier has quotas. The 1h LRU cache helps; the recheck workflow batches and rate-limits its own calls.

## Alternatives considered

- **Skipping SSRF** because we never fetch URLs ourselves. Rejected: shortlinks to internal-network resources are still abusable (sharing them in a public chat reveals private URLs; URL-preview bots downstream might fetch them).
- **VirusTotal** instead of / in addition to Safe Browsing. Rejected for MVP — Safe Browsing is free and Google-backed; VirusTotal's free tier is much tighter. Phase 2 candidate.
- **Auth-gated rate limiting** (per-account instead of per-IP). Rejected: MVP has no auth.
- **Block-list at nginx** for known bad IPs. Rejected: orthogonal to URL safety; out of scope.

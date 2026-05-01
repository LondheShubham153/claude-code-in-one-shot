"""Google Safe Browsing v4 client.

Used by:
- Synchronous shorten path (POST /api/links): fail-open on Google flake; skip
  entirely if SAFE_BROWSING_API_KEY is unset.
- Daily Temporal recheck workflow: retried via activity retry policy.

LRU-caches negative results for 1h to avoid re-querying Google on bursts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
_THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]
_PLATFORM_TYPES = ["ANY_PLATFORM"]
_THREAT_ENTRY_TYPES = ["URL"]

_NEG_CACHE_TTL = 3600.0  # 1 hour


@dataclass
class SafeBrowsingResult:
    safe: bool
    skipped: bool = False
    reason: str | None = None
    threat_types: list[str] = field(default_factory=list)


_neg_cache: dict[str, float] = {}
_lock = asyncio.Lock()


def _is_neg_cached(url: str) -> bool:
    expiry = _neg_cache.get(url)
    if expiry is None:
        return False
    if time.monotonic() > expiry:
        _neg_cache.pop(url, None)
        return False
    return True


async def check_url(url: str, *, client: httpx.AsyncClient | None = None) -> SafeBrowsingResult:
    settings = get_settings()
    if not settings.SAFE_BROWSING_API_KEY:
        return SafeBrowsingResult(safe=True, skipped=True, reason="api_key_missing")

    if _is_neg_cached(url):
        return SafeBrowsingResult(safe=True, skipped=False, reason="neg_cache")

    payload = {
        "client": {"clientId": "urlshortener", "clientVersion": "0.1.0"},
        "threatInfo": {
            "threatTypes": _THREAT_TYPES,
            "platformTypes": _PLATFORM_TYPES,
            "threatEntryTypes": _THREAT_ENTRY_TYPES,
            "threatEntries": [{"url": url}],
        },
    }

    own_client = client is None
    c = client or httpx.AsyncClient(timeout=httpx.Timeout(3.0))
    try:
        resp = await c.post(
            API_URL,
            params={"key": settings.SAFE_BROWSING_API_KEY},
            json=payload,
        )
        if resp.status_code != 200:
            logger.warning(
                "safe_browsing non-200",
                extra={"status": resp.status_code, "body": resp.text[:200]},
            )
            return SafeBrowsingResult(safe=True, skipped=True, reason=f"http_{resp.status_code}")
        data = resp.json()
        matches = data.get("matches") or []
        if matches:
            types = sorted({m.get("threatType", "?") for m in matches})
            return SafeBrowsingResult(safe=False, threat_types=types)
        # Negative result — cache.
        async with _lock:
            _neg_cache[url] = time.monotonic() + _NEG_CACHE_TTL
        return SafeBrowsingResult(safe=True)
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("safe_browsing network error: %s", exc)
        return SafeBrowsingResult(safe=True, skipped=True, reason="network_error")
    finally:
        if own_client:
            await c.aclose()

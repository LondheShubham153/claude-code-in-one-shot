"""URL validation: scheme allowlist + private/reserved IP block (SSRF guard).

Notes on DNS rebinding: we resolve the host at validation time but never
fetch the URL ourselves at redirect time (we 302). So the rebinding window is
only meaningful for clients on the same private network as the operator,
which is no worse than them entering the URL directly. Documented in ADR 0003.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from app.config import get_settings

logger = logging.getLogger(__name__)


class UnsafeURLError(ValueError):
    """Raised when a URL fails any validation check."""


_LITERAL_DENYLIST = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block to be safe
    return any(
        [
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        ]
    )


def _resolve_addresses(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve host: {host} ({exc})") from exc
    return list({info[4][0] for info in infos})


def validate_url(url: str) -> None:
    """Raise UnsafeURLError on any failure. Returns None on success."""
    settings = get_settings()

    if len(url) > settings.MAX_URL_LENGTH:
        raise UnsafeURLError(f"url exceeds max length of {settings.MAX_URL_LENGTH}")

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in settings.ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme '{scheme}' not in allowlist {settings.ALLOWED_SCHEMES}")

    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeURLError("missing hostname")

    if host in _LITERAL_DENYLIST:
        raise UnsafeURLError(f"host '{host}' is blocked")

    if not settings.BLOCK_PRIVATE_IPS:
        return

    # If the host is itself an IP literal, check directly.
    try:
        ipaddress.ip_address(host)
        if _is_blocked_ip(host):
            raise UnsafeURLError(f"host '{host}' resolves to a blocked address")
        return
    except ValueError:
        pass  # not an IP literal — resolve via DNS

    # Resolve and reject if any address is blocked.
    addresses = _resolve_addresses(host)
    blocked = [addr for addr in addresses if _is_blocked_ip(addr)]
    if blocked:
        raise UnsafeURLError(
            f"host '{host}' resolves to blocked address(es): {sorted(blocked)}"
        )

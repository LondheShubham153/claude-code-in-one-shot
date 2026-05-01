"""Pure unit tests for URL validation — no DB, no network."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.url_validator import UnsafeURLError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "http://example.com/path?q=1",
        "https://anthropic.com/",
        "https://www.iana.org/help/example-domains",  # iana.org is a stable resolvable host
    ],
)
def test_valid_urls_pass(url: str) -> None:
    # example.com etc. resolve to public IPs; we expect no exception.
    validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/html,<script>alert(1)</script>",
        "ssh://example.com",
        "ws://example.com",
    ],
)
def test_disallowed_schemes_rejected(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://localhost:8000/",
        "http://127.0.0.1/",
        "http://127.0.0.1:80/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata service
        "http://[::1]/",
        "http://[fe80::1]/",
    ],
)
def test_private_and_reserved_ips_blocked(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_excessive_length_rejected() -> None:
    long = "https://example.com/" + ("a" * 3000)
    with pytest.raises(UnsafeURLError):
        validate_url(long)


def test_dns_resolved_private_ip_blocked() -> None:
    """Hostname that resolves to a private IP must be blocked even if it parses fine."""
    with patch("app.services.url_validator._resolve_addresses", return_value=["10.0.0.5"]):
        with pytest.raises(UnsafeURLError):
            validate_url("http://internal.corp/")


def test_dns_resolved_mixed_addresses_blocked() -> None:
    """If ANY resolved address is private, block."""
    with patch(
        "app.services.url_validator._resolve_addresses",
        return_value=["1.2.3.4", "192.168.1.10"],
    ):
        with pytest.raises(UnsafeURLError):
            validate_url("http://mixed.example/")


def test_missing_hostname_rejected() -> None:
    with pytest.raises(UnsafeURLError):
        validate_url("https:///path")

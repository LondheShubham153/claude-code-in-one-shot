"""Safe Browsing client tests — respx-mocked HTTP."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.services import safe_browsing
from app.services.safe_browsing import check_url as _real_check_url


@pytest.fixture(autouse=True)
def _restore_real_safe_browsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conftest installs an autouse mock on `safe_browsing.check_url`. These
    tests want to exercise the real client, so restore the original
    reference (captured at import time, before the conftest patch ran)."""
    monkeypatch.setattr(safe_browsing, "check_url", _real_check_url)


@pytest.fixture
def with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    # Clear the LRU negative cache between tests
    safe_browsing._neg_cache.clear()


@pytest.mark.asyncio
async def test_no_api_key_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    safe_browsing._neg_cache.clear()

    result = await _real_check_url("https://example.com")
    assert result.safe is True
    assert result.skipped is True
    assert result.reason == "api_key_missing"


@pytest.mark.asyncio
async def test_clean_url_passes(with_api_key) -> None:  # noqa: ARG001
    with respx.mock:
        respx.post(safe_browsing.API_URL).mock(return_value=Response(200, json={}))
        result = await _real_check_url("https://example.com")
    assert result.safe is True
    assert result.skipped is False


@pytest.mark.asyncio
async def test_flagged_url_blocked(with_api_key) -> None:  # noqa: ARG001
    body = {
        "matches": [
            {"threatType": "MALWARE", "platformType": "ANY_PLATFORM"},
            {"threatType": "SOCIAL_ENGINEERING", "platformType": "ANY_PLATFORM"},
        ]
    }
    with respx.mock:
        respx.post(safe_browsing.API_URL).mock(return_value=Response(200, json=body))
        result = await _real_check_url("https://malicious.test/")
    assert result.safe is False
    assert "MALWARE" in result.threat_types


@pytest.mark.asyncio
async def test_network_error_fail_open(with_api_key) -> None:  # noqa: ARG001
    import httpx

    with respx.mock:
        respx.post(safe_browsing.API_URL).mock(
            side_effect=httpx.ConnectTimeout("simulated timeout")
        )
        result = await _real_check_url("https://example.com")
    assert result.safe is True  # fail-open
    assert result.skipped is True
    assert result.reason == "network_error"


@pytest.mark.asyncio
async def test_5xx_fail_open(with_api_key) -> None:  # noqa: ARG001
    with respx.mock:
        respx.post(safe_browsing.API_URL).mock(return_value=Response(503, text="oops"))
        result = await _real_check_url("https://example.com")
    assert result.safe is True
    assert result.skipped is True
    assert result.reason == "http_503"

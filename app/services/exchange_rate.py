"""INR -> USD exchange rate via exchangerate-api.com open endpoint.

The open endpoint doesn't require an API key. We cache the rate for 6 hours
per process to avoid hammering the API on every price suggestion.
"""
from __future__ import annotations

import logging
import time
import urllib.request
import json
from typing import Optional

logger = logging.getLogger(__name__)

_OPEN_ENDPOINT = "https://open.er-api.com/v6/latest/INR"
_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_FALLBACK_INR_TO_USD = 0.012  # used only if the API is unreachable

_cache: dict = {"rate": None, "fetched_at": 0.0}


def inr_to_usd(amount_inr: float) -> Optional[float]:
    """Convert INR amount to USD. Returns None only on extreme failure."""
    rate = _get_rate()
    if rate is None:
        return None
    return round(amount_inr * rate, 2)


def get_rate() -> Optional[float]:
    """Expose the current INR->USD rate for callers that want it."""
    return _get_rate()


def _get_rate() -> Optional[float]:
    now = time.time()
    if _cache["rate"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["rate"]

    try:
        req = urllib.request.Request(
            _OPEN_ENDPOINT,
            headers={"User-Agent": "tulacraft/price-suggestion"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("result") != "success":
            raise RuntimeError(f"exchangerate-api returned non-success: {data.get('result')}")
        rate = data["rates"]["USD"]
        _cache["rate"] = float(rate)
        _cache["fetched_at"] = now
        return _cache["rate"]
    except Exception as exc:
        logger.warning("exchangerate-api fetch failed: %s; using fallback %s", exc, _FALLBACK_INR_TO_USD)
        if _cache["rate"] is not None:
            return _cache["rate"]  # serve stale rather than nothing
        return _FALLBACK_INR_TO_USD

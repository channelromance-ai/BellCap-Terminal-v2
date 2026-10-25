"""
One way to ask the internet for something.

Every source goes through `get`, so timeouts, retries and the identifying
User-Agent live in one place. Requests say plainly that they come from this
engine; a source that only answers browsers is a source we don't use.

Nothing here retries a 4xx other than 429: a 403 or 404 means the address or
the rules changed, and hammering it will not change them back.
"""

from __future__ import annotations

import time

import requests

UA = "BellCap-Terminal/2.0 (personal macro research; python-requests)"


SECRET_PARAMS = ("apikey", "api_key")


class FetchError(RuntimeError):
    pass


def _redact(text: str, params: dict | None) -> str:
    """Network errors can quote the full URL; never let a key ride along."""
    for name in SECRET_PARAMS:
        secret = (params or {}).get(name)
        if secret:
            text = text.replace(str(secret), "***")
    return text


def get(url: str, *, params: dict | None = None, timeout: float = 30,
        retries: int = 3, headers: dict | None = None) -> bytes:
    """Return the response body, or raise FetchError saying why not."""
    hdrs = {"User-Agent": UA, "Accept": "*/*", **(headers or {})}
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if r.status_code == 200:
                return r.content
            last = f"HTTP {r.status_code}"
            if r.status_code != 429 and r.status_code < 500:
                break
        except requests.RequestException as e:
            last = _redact(f"{type(e).__name__}: {e}", params)
        time.sleep(2 * (attempt + 1))
    raise FetchError(f"{url.split('?')[0]} -> {last}")

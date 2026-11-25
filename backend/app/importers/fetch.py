"""A polite HTTP client for the importers.

- identifies itself with a User-Agent
- waits at least a second between requests to the same site
- retries a couple of times on network errors and 5xx responses
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "IronRod/1.0 (self-hosted personal scripture study; https://github.com/ShaquilleOatmeal76/ironrod)"
DELAY_S = 1.0
_last: dict[str, float] = {}


class FetchError(Exception):
    pass


def get(url: str, *, accept: str = "*/*", retries: int = 2, timeout: int = 30) -> str | None:
    """Fetch a URL and return its text, or None on 404."""
    host = urllib.parse.urlsplit(url).netloc
    for attempt in range(retries + 1):
        wait = DELAY_S - (time.time() - _last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                _last[host] = time.time()
                return res.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            _last[host] = time.time()
            if e.code == 404:
                return None
            if e.code < 500 or attempt == retries:
                raise FetchError(f"{e.code} from {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            _last[host] = time.time()
            if attempt == retries:
                raise FetchError(f"couldn't reach {host}: {e}") from e
        time.sleep(2 * (attempt + 1))
    return None


def get_json(url: str) -> dict | None:
    text = get(url, accept="application/json")
    return json.loads(text) if text else None

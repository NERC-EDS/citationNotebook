"""One HTTP client for every stage: retries, timeouts, a polite User-Agent and per-host pacing."""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, TypeVar
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CODE_VERSION

log = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

# Minimum seconds between requests to one host, across all threads.
HOST_INTERVAL = {
    "api.datacite.org": 0.05,
    "api.crossref.org": 0.05,
    "api.scholexplorer.openaire.eu": 0.1,
    "app.overton.io": 1.05,     # Overton asks for at most one request a second
    "doi.org": 0.05,
}

_SECRET = re.compile(r"(api_key=)[^&\s]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Hide API keys in URLs before they reach a log or an error message."""
    return _SECRET.sub(r"\1***", str(text))


class HttpError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, mailto: str | None = None, workers: int = 4, timeout=(10, 90)):
        self.mailto = mailto
        self.workers = max(1, workers)
        self.timeout = timeout
        self.user_agent = (
            f"NERC-EDS-citations/{CODE_VERSION} (+https://github.com/NERC-EDS/citationNotebook"
            + (f"; mailto:{mailto}" if mailto else "") + ")"
        )
        self._local = threading.local()
        self._pace_lock = threading.Lock()
        self._last_call: dict[str, float] = {}

    # -- sessions -----------------------------------------------------------
    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            retry = Retry(
                total=6,
                backoff_factor=1.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET", "POST"),
                respect_retry_after_header=True,
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            session.headers.update({"User-Agent": self.user_agent})
            self._local.session = session
        return session

    def _pace(self, url: str):
        host = urlsplit(url).netloc
        interval = HOST_INTERVAL.get(host, 0)
        if not interval:
            return
        with self._pace_lock:
            wait = self._last_call.get(host, 0) + interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_call[host] = time.monotonic()

    # -- requests -----------------------------------------------------------
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self._pace(url)
        kwargs.setdefault("timeout", self.timeout)
        try:
            return self._session().request(method, url, **kwargs)
        except requests.RequestException as error:
            raise HttpError(redact(f"{method} {url}: {error}")) from None

    def get(self, url: str, params=None, headers=None, **kwargs) -> requests.Response:
        return self.request("GET", url, params=params, headers=headers, **kwargs)

    def get_json(self, url: str, params=None, headers=None, allow_404: bool = True):
        """Parsed JSON, or None for a 404 when allow_404. Anything else non-200 raises HttpError."""
        response = self.get(url, params=params, headers={"Accept": "application/json", **(headers or {})})
        if response.status_code == 404 and allow_404:
            return None
        if response.status_code != 200:
            raise HttpError(redact(f"GET {response.url}: HTTP {response.status_code} {response.text[:200]!r}"))
        try:
            return response.json()
        except ValueError:
            raise HttpError(redact(f"GET {response.url}: response is not JSON")) from None

    def post_json(self, url: str, data=None, headers=None):
        response = self.request("POST", url, data=data, headers={"Accept": "application/json", **(headers or {})})
        if response.status_code != 200:
            raise HttpError(redact(f"POST {url}: HTTP {response.status_code} {response.text[:200]!r}"))
        try:
            return response.json()
        except ValueError:
            raise HttpError(redact(f"POST {url}: response is not JSON")) from None

    # -- concurrency ----------------------------------------------------------
    def map(self, fn: Callable[[T], R], items: Iterable[T]):
        """Yield (item, result, error) for each item, running fn in worker threads.

        Results arrive in input order. Errors are returned, not raised, so one bad
        DOI cannot stop a harvest; the caller decides what an error rate means.
        """
        items = list(items)

        def safe(item):
            try:
                return item, fn(item), None
            except Exception as error:  # noqa: BLE001 - reported per item
                return item, None, error

        if self.workers == 1:
            for item in items:
                yield safe(item)
            return
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            yield from pool.map(safe, items)

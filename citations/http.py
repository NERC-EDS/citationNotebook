"""One HTTP client for every stage: retries, timeouts, a polite User-Agent, and each API's rate limit."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CODE_VERSION

log = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")



@dataclass(frozen=True)
class Limit:
    rate: float       # requests per second, across all threads
    concurrent: int   # requests in flight at once, shared by every bucket in `group`
    group: str


def api_limits(polite: bool) -> dict[str, Limit]:
    """Each API's published limit, a little under it. `polite`: requests carry a contact email.

    Crossref (from Dec 2025): polite pool 10/s for single records and 3/s for lists,
    3 requests at once; public pool 5/s and 1/s, one at a time.
    https://crossref.org/blog/announcing-changes-to-rest-api-rate-limits/
    DataCite: 1,000 requests per 5 minutes per IP with contact details, 500 without;
    doi.org content negotiation for DataCite DOIs has its own cap of 1,000 per 5 minutes.
    https://support.datacite.org/docs/rate-limit
    Scholexplorer publishes none (v3 used 10/s); Overton asks for one request a second.
    """
    crossref_at_once = 3 if polite else 1
    return {
        "api.crossref.org/single": Limit(9 if polite else 4.5, crossref_at_once, "crossref"),
        "api.crossref.org/list": Limit(2.7 if polite else 0.9, crossref_at_once, "crossref"),
        "doi.org/crossref": Limit(9 if polite else 4.5, crossref_at_once, "crossref"),
        "api.datacite.org": Limit(3.2 if polite else 1.6, 4, "datacite"),
        "doi.org/datacite": Limit(3.2 if polite else 1.6, 4, "datacite-cn"),
        "api.scholexplorer.openaire.eu": Limit(10, 4, "scholexplorer"),
        "app.overton.io": Limit(0.95, 1, "overton"),
    }


def bucket_for(url: str) -> str:
    """The rate-limit bucket of a request: its host, and for Crossref whether it reads one record or a list."""
    parts = urlsplit(url)
    if parts.netloc == "api.crossref.org":
        single = re.match(r"^(/v1)?/works/.+", parts.path)   # /works/{doi}; /works?query is a list
        return "api.crossref.org/single" if single else "api.crossref.org/list"
    return parts.netloc


def throttled_count(response) -> int:
    """How many 429 (rate limited) responses a request got, retries included."""
    retries = getattr(getattr(response, "raw", None), "retries", None)
    history = getattr(retries, "history", None) or ()
    return sum(getattr(h, "status", None) == 429 for h in history) + (getattr(response, "status_code", None) == 429)

_SECRET = re.compile(r"(api_key=)[^&\s]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Hide API keys in URLs before they reach a log or an error message."""
    return _SECRET.sub(r"\1***", str(text))


class HttpError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, mailto: str | None = None, workers: int = 4, timeout=(10, 90), limits=None):
        self.mailto = mailto
        self.workers = max(1, workers)
        self.timeout = timeout
        self.user_agent = (
            f"NERC-EDS-citations/{CODE_VERSION} (+https://github.com/NERC-EDS/citationNotebook"
            + (f"; mailto:{mailto}" if mailto else "") + ")"
        )
        self.limits = limits if limits is not None else api_limits(polite=bool(mailto))
        self._local = threading.local()
        self._pace_lock = threading.Lock()
        self._next_slot: dict[str, float] = {}
        self._groups: dict[str, threading.BoundedSemaphore] = {}
        for limit in self.limits.values():
            self._groups.setdefault(limit.group, threading.BoundedSemaphore(limit.concurrent))
        self._throttled = Counter()

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

    # -- rate limits ---------------------------------------------------------
    @contextmanager
    def limited(self, bucket: str | None):
        """Wait for a free slot and a turn in `bucket`'s limit, then hold the slot while the request runs."""
        limit = self.limits.get(bucket)
        if limit is None:
            yield
            return
        with self._groups[limit.group]:
            # Book the next turn under the lock and sleep outside it, so a slow API
            # (Overton, once a second) never holds up requests to the others.
            with self._pace_lock:
                now = time.monotonic()
                turn = max(now, self._next_slot.get(bucket, 0.0))
                self._next_slot[bucket] = turn + 1 / limit.rate
            if turn > now:
                time.sleep(turn - now)
            yield

    def observe(self, bucket: str, response):
        """Count the 429s a response got, so a run can report how often each API throttled it."""
        n = throttled_count(response)
        if n:
            with self._pace_lock:
                self._throttled[bucket] += n

    def throttled(self) -> dict:
        """429 responses so far, by rate-limit bucket."""
        with self._pace_lock:
            return dict(self._throttled)

    # -- requests -----------------------------------------------------------
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        bucket = bucket_for(url)
        try:
            with self.limited(bucket):
                response = self._session().request(method, url, **kwargs)
        except requests.RequestException as error:
            raise HttpError(redact(f"{method} {url}: {error}")) from None
        self.observe(bucket, response)
        return response

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

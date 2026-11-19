"""Offline test helpers: a fake HTTP client that answers from Python functions."""

from __future__ import annotations

from urllib.parse import parse_qsl, unquote, urlsplit

import pytest

from citations import db
from citations.config import Settings
from citations.harvest import Context
from citations.http import HttpError


class FakeClient:
    """Routes requests to handlers: handler(path, params) -> JSON, None (404) or raises."""

    def __init__(self, routes, mailto=None):
        self.routes = routes        # {(host, path_prefix): handler}
        self.mailto = mailto
        self.calls = []
        self.workers = 1

    def _route(self, url, params):
        parts = urlsplit(url)
        merged = dict(parse_qsl(parts.query))
        merged.update({k: str(v) for k, v in (params or {}).items()})
        path = unquote(parts.path)
        self.calls.append((parts.netloc, path, merged))
        for (host, prefix), handler in self.routes.items():
            if parts.netloc == host and path.startswith(prefix):
                return handler(path, merged)
        raise AssertionError(f"unexpected request {url} {params}")

    def get_json(self, url, params=None, headers=None, allow_404=True):
        result = self._route(url, params)
        if result is None and not allow_404:
            raise HttpError(f"GET {url}: HTTP 404")
        return result

    def post_json(self, url, data=None, headers=None):
        return self._route(url, data)

    def map(self, fn, items):
        for item in items:
            try:
                yield item, fn(item), None
            except Exception as error:  # noqa: BLE001
                yield item, None, error


@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "citations.sqlite", results_dir=tmp_path / "Results", workers=1,
                    mailto=None, overton_api_key="test-key")


@pytest.fixture
def con(settings):
    connection = db.connect(settings.db_path)
    yield connection
    connection.close()


def make_ctx(con, client, settings):
    return Context(con=con, client=client, settings=settings)

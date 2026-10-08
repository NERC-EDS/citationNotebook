"""Running a source harvest: resume, error rate, row-drop check and the switch to the new good run."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from . import db
from .config import ALL_SOURCES, Settings
from .http import HttpClient, redact

log = logging.getLogger(__name__)


class SourceSkipped(Exception):
    """The source cannot run in this environment (for example no API key); not a failure of the data."""


class NoInventory(RuntimeError):
    pass


@dataclass
class Context:
    con: object
    client: HttpClient
    settings: Settings
    _datasets: list | None = field(default=None, repr=False)

    def datasets(self) -> list:
        """The current (last good) inventory, as sqlite rows."""
        if self._datasets is None:
            if db.good_run(self.con, "inventory") is None:
                raise NoInventory("No successful inventory yet: run `python -m citations inventory` first.")
            self._datasets = self.con.execute("SELECT * FROM datasets ORDER BY doi").fetchall()
        return self._datasets

    def dataset_dois(self) -> set:
        return {row["doi"] for row in self.datasets()}


class Tally:
    """Thread-safe counters for what a source dropped or could not map."""

    def __init__(self):
        import threading
        from collections import Counter

        self._lock = threading.Lock()
        self.counts = Counter()

    def add(self, key: str, n: int = 1):
        with self._lock:
            self.counts[key] += n

    def as_dict(self) -> dict:
        with self._lock:
            return dict(sorted(self.counts.items()))


@dataclass
class RawLink:
    data_doi: str
    citing_id: str
    citing_id_type: str
    relation_type: str
    source_relation: str
    provenance: str
    hint: dict | None = None


def write_links(con, source: str, run_id: int, links: list[RawLink]):
    con.executemany(
        "INSERT OR IGNORE INTO raw_links (source, run_id, data_doi, citing_id, citing_id_type, relation_type, "
        "source_relation, provenance, hint) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (source, run_id, l.data_doi, l.citing_id, l.citing_id_type, l.relation_type, l.source_relation,
             l.provenance, json.dumps(l.hint, ensure_ascii=False, sort_keys=True) if l.hint else None)
            for l in links
        ],
    )


def log_fetch(con, source: str, run_id: int, key: str, status: str, n: int | None = None, message: str | None = None):
    con.execute(
        "INSERT INTO fetch_log (source, run_id, key, status, n, message, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(source, run_id, key) DO UPDATE SET status=excluded.status, n=excluded.n, "
        "message=excluded.message, fetched_at=excluded.fetched_at",
        (source, run_id, key, status, n, redact(message) if message else None, db.now_iso()),
    )


def done_keys(con, source: str, run_id: int) -> set:
    rows = con.execute("SELECT key FROM fetch_log WHERE source=? AND run_id=? AND status='ok'", (source, run_id))
    return {row["key"] for row in rows}


def per_key(ctx: Context, source: str, run_id: int, keys, fetch_one, commit_every: int = 200):
    """Fetch each key in worker threads and store its links as it arrives.

    fetch_one(key) -> list[RawLink]. Keys already fetched in this run are skipped,
    which is what makes a harvest resumable. Returns (items, errors) for this call.
    """
    keys = [k for k in keys if k not in done_keys(ctx.con, source, run_id)]
    items = errors = 0
    first_errors = []
    for i, (key, links, error) in enumerate(ctx.client.map(fetch_one, keys), 1):
        items += 1
        if error is not None:
            errors += 1
            if len(first_errors) < 5:
                first_errors.append(f"{key}: {redact(error)}")
            log_fetch(ctx.con, source, run_id, key, "error", message=str(error)[:500])
        else:
            write_links(ctx.con, source, run_id, links)
            log_fetch(ctx.con, source, run_id, key, "ok", n=len(links))
        if i % commit_every == 0:
            ctx.con.commit()
            log.info("%s: %d/%d keys, %d errors", source, i, len(keys), errors)
    ctx.con.commit()
    for message in first_errors:
        log.warning("%s: %s", source, message)
    return items, errors


def run_harvest(ctx: Context, source: str, resume: bool = True) -> str:
    """Harvest one source; returns the run status."""
    from .sources import MODULES

    if source not in ALL_SOURCES:
        raise ValueError(f"Unknown source {source!r}; choose from {', '.join(ALL_SOURCES)}")
    module = MODULES[source]
    con, settings = ctx.con, ctx.settings
    ctx.datasets()  # fail early without an inventory

    previous = db.resumable_run(con, source, settings.resume_window_days) if resume else None
    if previous is not None:
        run_id = previous["run_id"]
        con.execute("UPDATE runs SET status='running' WHERE run_id=?", (run_id,))
        con.commit()
        log.info("%s: resuming run %d started %s", source, run_id, previous["started_at"])
    else:
        run_id = db.start_run(con, "harvest", source)
        log.info("%s: starting run %d", source, run_id)

    try:
        stats = module.harvest(ctx, run_id)
    except SourceSkipped as reason:
        db.finish_run(con, run_id, "skipped", message=str(reason))
        log.warning("%s: skipped (%s)", source, reason)
        return "skipped"
    except Exception as error:  # noqa: BLE001 - recorded, and the stage reports failure
        con.commit()
        db.finish_run(con, run_id, "failed", message=redact(f"{type(error).__name__}: {error}")[:1000])
        log.error("%s: failed: %s", source, redact(error))
        return "failed"

    total_items = con.execute(
        "SELECT COUNT(*) FROM fetch_log WHERE source=? AND run_id=?", (source, run_id)).fetchone()[0]
    total_errors = con.execute(
        "SELECT COUNT(*) FROM fetch_log WHERE source=? AND run_id=? AND status='error'", (source, run_id)).fetchone()[0]
    rows = con.execute("SELECT COUNT(*) FROM raw_links WHERE source=? AND run_id=?", (source, run_id)).fetchone()[0]
    details = dict(stats.get("details", {}))
    error_rate = total_errors / total_items if total_items else 0.0
    good = db.good_run(con, source)

    if error_rate > settings.max_error_rate:
        status = "partial"
        message = (f"{total_errors} of {total_items} requests failed ({error_rate:.1%}); "
                   "the next run resumes and retries them. Previous good harvest kept.")
    elif good is not None and good["rows"] and rows < good["rows"] * (1 - settings.max_row_drop):
        status = "rejected"
        message = (f"{rows} links against {good['rows']} in the last good harvest "
                   f"(a drop of more than {settings.max_row_drop:.0%}). Previous good harvest kept.")
    else:
        status = "success"
        message = None

    if status == "success":
        with db.transaction(con):
            db.set_good_run(con, source, run_id, rows)
            db.prune_harvests(con, source, run_id)
    db.finish_run(con, run_id, status, rows=rows, items=total_items, errors=total_errors, message=message,
                  details=details)
    (log.info if status == "success" else log.error)(
        "%s: %s, %d links from %d requests (%d errors)%s", source, status, rows, total_items, total_errors,
        f": {message}" if message else "")
    return status

"""SQLite store for every stage's intermediate data.

One file (``data/citations.sqlite`` by default) replaces the pickles in
``Results/intermediate_data``. Each harvest is a *run*; a source's links are
only used once its run finishes successfully, and ``source_state`` points at
the latest good run, so a failed or partial harvest never replaces good data.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import CODE_VERSION

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    stage        TEXT NOT NULL,     -- inventory | harvest | works | merge | publish
    source       TEXT,              -- harvest only: datacite | scholexplorer | overton | crossref
    status       TEXT NOT NULL,     -- running | success | partial | failed | rejected | skipped | blocked
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    rows         INTEGER,
    items        INTEGER,           -- DOIs (or other keys) queried
    errors       INTEGER,
    message      TEXT,
    details      TEXT,              -- JSON
    code_version TEXT
);

CREATE TABLE IF NOT EXISTS source_state (
    source           TEXT PRIMARY KEY,   -- 'inventory' or a harvest source
    good_run_id      INTEGER NOT NULL,
    good_finished_at TEXT NOT NULL,
    rows             INTEGER
);

CREATE TABLE IF NOT EXISTS datasets (
    doi                     TEXT PRIMARY KEY,
    data_centre             TEXT,
    publisher               TEXT,
    title                   TEXT,
    publication_year        INTEGER,
    resource_type_general   TEXT,
    registered              TEXT,
    authors                 TEXT,       -- JSON list of {name, given, family, orcid}
    datacite_citation_count INTEGER,
    run_id                  INTEGER
);
CREATE TABLE IF NOT EXISTS datasets_new AS SELECT * FROM datasets WHERE 0;

CREATE TABLE IF NOT EXISTS dataset_relations (
    doi           TEXT NOT NULL,
    relation_type TEXT,                 -- DataCite relationType, from the dataset's side
    related_raw   TEXT,
    related_type  TEXT,                 -- DataCite relatedIdentifierType
    run_id        INTEGER
);
CREATE TABLE IF NOT EXISTS dataset_relations_new AS SELECT * FROM dataset_relations WHERE 0;
CREATE INDEX IF NOT EXISTS dataset_relations_doi ON dataset_relations (doi);

CREATE TABLE IF NOT EXISTS raw_links (
    source          TEXT NOT NULL,
    run_id          INTEGER NOT NULL,
    data_doi        TEXT NOT NULL,
    citing_id       TEXT NOT NULL,
    citing_id_type  TEXT NOT NULL,      -- doi | url | pmid | pmc | handle
    relation_type   TEXT NOT NULL,      -- DataCite vocabulary, from the dataset's side
    source_relation TEXT NOT NULL,      -- the relation exactly as the source reported it
    provenance      TEXT NOT NULL,      -- finer origin, e.g. a DataCite event source-id
    hint            TEXT,               -- JSON: what the source said about the citing work
    PRIMARY KEY (source, run_id, data_doi, citing_id, source_relation, provenance)
);
CREATE INDEX IF NOT EXISTS raw_links_run ON raw_links (source, run_id);

CREATE TABLE IF NOT EXISTS fetch_log (
    source     TEXT NOT NULL,
    run_id     INTEGER NOT NULL,
    key        TEXT NOT NULL,
    status     TEXT NOT NULL,           -- ok | error
    n          INTEGER,
    message    TEXT,
    fetched_at TEXT,
    PRIMARY KEY (source, run_id, key)
);

CREATE TABLE IF NOT EXISTS works (
    citing_id           TEXT PRIMARY KEY,
    citing_id_type      TEXT,
    title               TEXT,
    work_type           TEXT,           -- CSL type where known
    container_title     TEXT,
    publisher           TEXT,
    issued              TEXT,           -- ISO 8601: YYYY, YYYY-MM or YYYY-MM-DD
    issued_precision    TEXT,           -- year | month | day
    authors             TEXT,           -- JSON list of {name, given, family, orcid}
    citation_text       TEXT,
    citation_source     TEXT,           -- formatter | reused | fallback
    metadata_source     TEXT,           -- crossref | datacite | inventory | scholexplorer | overton | crossref-datacitations
    fetched_at          TEXT,
    citation_fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS links (
    link_id          TEXT PRIMARY KEY,
    data_doi         TEXT NOT NULL,
    data_centre      TEXT,
    citing_id        TEXT NOT NULL,
    citing_id_type   TEXT NOT NULL,
    relation_type    TEXT NOT NULL,
    relation_class   TEXT NOT NULL,
    counted          INTEGER NOT NULL,
    status           TEXT NOT NULL,
    exclusion_reason TEXT,
    sources          TEXT NOT NULL,     -- JSON list
    source_relations TEXT NOT NULL,     -- JSON object: source -> [raw relations]
    first_seen       TEXT NOT NULL,
    last_seen        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS link_history (
    link_id    TEXT PRIMARY KEY,
    data_doi   TEXT NOT NULL,
    citing_id  TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def age_days(value: str | None, now: datetime | None = None) -> float | None:
    then = parse_iso(value)
    if then is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - then).total_seconds() / 86400


def connect(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
    con.commit()
    return con


@contextmanager
def transaction(con: sqlite3.Connection):
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise


def start_run(con, stage: str, source: str | None = None) -> int:
    cur = con.execute(
        "INSERT INTO runs (stage, source, status, started_at, code_version) VALUES (?, ?, 'running', ?, ?)",
        (stage, source, now_iso(), CODE_VERSION),
    )
    con.commit()
    return cur.lastrowid


def finish_run(con, run_id: int, status: str, rows=None, items=None, errors=None, message=None, details=None):
    con.execute(
        "UPDATE runs SET status=?, finished_at=?, rows=?, items=?, errors=?, message=?, details=? WHERE run_id=?",
        (status, now_iso(), rows, items, errors, message,
         json.dumps(details, sort_keys=True) if details is not None else None, run_id),
    )
    con.commit()


def get_run(con, run_id: int):
    return con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()


def latest_run(con, stage: str, source: str | None = None):
    if source is None:
        return con.execute("SELECT * FROM runs WHERE stage=? ORDER BY run_id DESC LIMIT 1", (stage,)).fetchone()
    return con.execute(
        "SELECT * FROM runs WHERE stage=? AND source=? ORDER BY run_id DESC LIMIT 1", (stage, source)
    ).fetchone()


def resumable_run(con, source: str, window_days: float):
    """An unfinished (running or partial) harvest of `source` young enough to resume, else None."""
    row = latest_run(con, "harvest", source)
    if row is None or row["status"] not in ("running", "partial"):
        return None
    age = age_days(row["started_at"])
    return row if age is not None and age <= window_days else None


def good_run(con, source: str):
    return con.execute("SELECT * FROM source_state WHERE source=?", (source,)).fetchone()


def set_good_run(con, source: str, run_id: int, rows: int | None):
    con.execute(
        "INSERT INTO source_state (source, good_run_id, good_finished_at, rows) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(source) DO UPDATE SET good_run_id=excluded.good_run_id, "
        "good_finished_at=excluded.good_finished_at, rows=excluded.rows",
        (source, run_id, now_iso(), rows),
    )


def prune_harvests(con, source: str, keep_run_id: int):
    """Drop raw links and fetch logs of older runs of `source`, keeping the good run."""
    con.execute("DELETE FROM raw_links WHERE source=? AND run_id<>?", (source, keep_run_id))
    con.execute("DELETE FROM fetch_log WHERE source=? AND run_id<>?", (source, keep_run_id))


def loads(value, default=None):
    if value in (None, ""):
        return default
    return json.loads(value)

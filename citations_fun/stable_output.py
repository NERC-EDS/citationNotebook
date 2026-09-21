"""
Deterministic writers for the result files this repo commits back to git.

Why this module exists
----------------------
The scheduled Actions re-run the whole pipeline and commit whatever comes out.
If the writing step isn't deterministic, git records a change even when the
science hasn't changed. Three separate causes were measured in this repo:

1. **Row / record order.** API pagination doesn't guarantee a stable order, so
   the same 6,300 records came back in a different sequence each run. One real
   pair of consecutive commits to `nerc_datacite_dois.json` shows 2,205 added /
   2,172 deleted lines for a net gain of *two* records.

2. **Volatile fields.** `data_page_number` and `data_self_link` record where a
   record happened to sit in the paginated response, so they change whenever
   the order does. Every consumer in this repo drops them, and they land in
   `Results/v3/latest_results.csv` as 100%-empty columns.

3. **Line endings.** `pandas.to_csv` writes the platform newline. The Actions
   runner writes LF; a Windows checkout writes CRLF, and every line of every
   file then shows as changed. Pinning `lineterminator="\\n"` here plus the
   `.gitattributes` rules makes the two agree.

Use `write_csv` / `write_json_records` / `write_json` instead of calling
`to_csv` / `json.dump` directly, and the output becomes a pure function of the
data.

Sorting notes
-------------
* Sorts are stable (`kind="mergesort"`) and sort on the *string* form of the
  key columns, so a column mixing ints, floats, None and str can't raise.
* NaNs sort last, consistently.
* Deduplication compares the string form of every column, so list-valued
  columns (`data_authors`, `pub_authors`) don't raise `TypeError: unhashable`
  the way plain `drop_duplicates()` does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Fields that describe *where a record appeared in a paginated response*, not
# the record itself. They change between runs for no useful reason.
VOLATILE_FIELDS = ("data_page_number", "data_self_link")

# The column order the intermediate per-source CSVs should use, so a schema
# change is a deliberate diff rather than an accident of dict ordering.
SOURCE_COLUMNS = [
    "data_doi",
    "data_publisher",
    "data_title",
    "data_publication_year",
    "data_authors",
    "relation_type",
    "pub_doi",
    "pub_title",
    "pub_date",
    "pub_authors",
    "pub_type",
    "pub_publisher",
    "source_id",
]


def _string_key(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Build a helper frame of stringified sort keys (NaN -> '~' so it sorts last)."""
    keys = {}
    for i, col in enumerate(columns):
        s = df[col]
        keys[f"__sort_{i}"] = s.astype("string").fillna("~").astype(str)
    return pd.DataFrame(keys, index=df.index)


def stable_frame(
    df: pd.DataFrame,
    sort_by,
    *,
    dedupe: bool = True,
    columns=None,
    drop_volatile: bool = False,
    int_columns=(),
) -> pd.DataFrame:
    """Return `df` in a canonical form: fixed columns, deduped, deterministically sorted.

    Parameters
    ----------
    sort_by : list of column names to sort on, in priority order. Columns that
        aren't present are skipped (so callers can pass a superset).
    dedupe : drop rows that are identical across *every* column. This does not
        merge rows that differ only in, say, relation_type - those are real.
    columns : optional explicit output column order. Missing ones are created
        empty so the schema stays constant even when a source returns nothing.
    drop_volatile : also drop VOLATILE_FIELDS.
    int_columns : coerce these to pandas' nullable "Int64" so a whole-number
        column always renders as `2012`, never `2012.0`.

        This is opt-in, and worth knowing about: pandas renders an integer
        column as float the moment it contains one null. `data_publication_year`
        is float-formatted today only because something is always missing - the
        first run where every year resolves would flip every row from `2012.0`
        to `2012` and show as a 100% diff. Passing the column here removes that
        risk permanently, at the cost of one deliberate reformatting commit.
    """
    out = df.copy()

    for col in int_columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    if drop_volatile:
        out = out.drop(columns=[c for c in VOLATILE_FIELDS if c in out.columns])

    if columns is not None:
        for c in columns:
            if c not in out.columns:
                out[c] = pd.NA
        out = out[list(columns)]

    if dedupe and len(out):
        # Compare the string form so list-valued cells don't blow up.
        out = out[~out.astype(str).duplicated(keep="first")]

    keys = [c for c in sort_by if c in out.columns]
    if keys and len(out):
        helper = _string_key(out, keys)
        out = out.loc[helper.sort_values(list(helper.columns), kind="mergesort").index]

    return out.reset_index(drop=True)


def write_csv(
    df: pd.DataFrame,
    path,
    sort_by,
    *,
    dedupe: bool = True,
    columns=None,
    drop_volatile: bool = False,
    int_columns=(),
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """Canonicalise `df` and write it as a CSV with LF endings. Returns the frame written."""
    out = stable_frame(
        df, sort_by, dedupe=dedupe, columns=columns,
        drop_volatile=drop_volatile, int_columns=int_columns,
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # lineterminator pins LF on every platform; index=False keeps the row
    # numbers (which shift whenever anything is inserted) out of the file.
    out.to_csv(path, index=False, encoding=encoding, lineterminator="\n")
    return out


def write_pickle(df: pd.DataFrame, path, sort_by, *, dedupe: bool = True,
                 columns=None, drop_volatile: bool = False) -> pd.DataFrame:
    """Write the same canonical frame as a pickle (the hand-off between workflows).

    Pickles are binary, so git can't diff them either way - but writing the
    canonical frame keeps the pickle and the CSV in step, and means the merge
    step downstream also sees rows in a stable order.
    """
    out = stable_frame(
        df, sort_by, dedupe=dedupe, columns=columns, drop_volatile=drop_volatile
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_pickle(path)
    return out


def write_json(obj, path, *, indent: int = 2, sort_keys: bool = True) -> None:
    """Write JSON pretty-printed, key-sorted, UTF-8, LF, with a trailing newline.

    Pretty-printing matters: `Results/v3/latest_results.json` is currently a
    single 2 MB line, so every commit replaces the whole blob and the diff is
    unreadable. One record per few lines makes the change reviewable.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


def write_json_records(
    records,
    path,
    sort_by=("data_doi",),
    *,
    dedupe: bool = True,
    drop_volatile: bool = True,
    indent: int = 2,
) -> list:
    """Sort, dedupe and write a list of flat dicts. Returns the list written."""
    rows = list(records)

    if drop_volatile:
        rows = [{k: v for k, v in r.items() if k not in VOLATILE_FIELDS} for r in rows]

    if dedupe:
        seen, deduped = set(), []
        for r in rows:
            fingerprint = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
            if fingerprint not in seen:
                seen.add(fingerprint)
                deduped.append(r)
        rows = deduped

    def key(record):
        # Primary keys first, then the whole record as a tie-breaker so records
        # sharing a DOI still land in a fixed order.
        return tuple(str(record.get(k, "")) for k in sort_by) + (
            json.dumps(record, sort_keys=True, ensure_ascii=False, default=str),
        )

    rows.sort(key=key)
    write_json(rows, path, indent=indent, sort_keys=True)
    return rows

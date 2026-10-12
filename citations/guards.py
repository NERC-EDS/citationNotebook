"""Publishing guards: never publish a broken or stale source as if it had found nothing.

v3 published whatever each stage last committed: the Scholexplorer harvest was
an empty file from 21 Jan to 29 Sep 2026 and v3 went out without it every week.
"""

from __future__ import annotations

import json
from collections import Counter

from . import db
from .config import ALL_SOURCES, OPTIONAL_SOURCES, REQUIRED_SOURCES


def source_report(con, settings) -> dict:
    report = {}
    for source in ("inventory",) + ALL_SOURCES:
        stage = "inventory" if source == "inventory" else "harvest"
        latest = db.latest_run(con, stage, None if source == "inventory" else source)
        good = db.good_run(con, source)
        age = db.age_days(good["good_finished_at"]) if good else None
        report[source] = {
            "required": source == "inventory" or source in REQUIRED_SOURCES,
            "latest_status": latest["status"] if latest else None,
            "latest_run_id": latest["run_id"] if latest else None,
            "latest_message": latest["message"] if latest else None,
            "good_run_id": good["good_run_id"] if good else None,
            "good_finished_at": good["good_finished_at"] if good else None,
            "good_rows": good["rows"] if good else None,
            "age_days": round(age, 2) if age is not None else None,
            "stale": age is None or age > settings.max_source_age_days,
        }
    return report


def links_by_source(con) -> dict:
    counts = Counter()
    for row in con.execute("SELECT sources FROM links"):
        for label in json.loads(row["sources"]):
            counts[label.split(":")[0]] += 1
    return dict(sorted(counts.items()))


def check(con, settings, previous_manifest: dict | None, reconciliation: dict | None) -> tuple[list, list, dict]:
    """(problems, warnings, report). Any problem blocks publishing unless forced."""
    problems, warnings = [], []
    report = source_report(con, settings)
    for source, info in report.items():
        target = problems if info["required"] else warnings
        if info["good_run_id"] is None:
            if info["required"] or info["latest_status"] not in (None, "skipped"):
                target.append(f"{source}: no successful harvest yet (latest: {info['latest_status']}).")
            continue
        if info["latest_status"] not in ("success", None):
            target.append(f"{source}: latest run {info['latest_run_id']} is {info['latest_status']}"
                          f"{': ' + info['latest_message'] if info['latest_message'] else ''}; "
                          f"its last good harvest is {info['age_days']} days old.")
        elif info["stale"]:
            target.append(f"{source}: last good harvest is {info['age_days']} days old "
                          f"(limit {settings.max_source_age_days}).")

    for stage in ("works", "merge"):
        latest = db.latest_run(con, stage)
        if latest is None or latest["status"] not in ("success", "partial"):
            problems.append(f"{stage}: latest run is {latest['status'] if latest else 'missing'}.")
        elif latest["status"] == "partial":
            warnings.append(f"{stage}: latest run is partial ({latest['errors']} errors); some metadata is missing.")

    current = links_by_source(con)
    before = ((previous_manifest or {}).get("counts") or {}).get("links_by_source") or {}
    for source, old in before.items():
        new = current.get(source, 0)
        if old and new < old * (1 - settings.max_row_drop):
            message = (f"{source}: {new} links against {old} in the last published results "
                       f"(a drop of more than {settings.max_row_drop:.0%}).")
            (problems if source in REQUIRED_SOURCES else warnings).append(message)

    if reconciliation and reconciliation.get("datacite_cited_datasets"):
        share = reconciliation["incomplete_share"]
        if share > settings.reconcile_threshold:
            problems.append(f"reconcile: {reconciliation['incomplete_datasets']} of "
                            f"{reconciliation['datacite_cited_datasets']} DataCite-cited datasets ({share:.1%}) "
                            f"have fewer harvested DataCite links than their citationCount "
                            f"(limit {settings.reconcile_threshold:.0%}).")
    for source in OPTIONAL_SOURCES:
        if report[source]["latest_status"] == "skipped":
            warnings.append(f"{source}: skipped ({report[source]['latest_message']}).")
    return problems, warnings, report

"""Exclusion rules. Excluded links stay in the results with a reason; nothing is silently dropped.

v3 deleted these rows (recording some in filtered_out_df.csv) and, until
Sept 2026, its pre-dates rule also dropped every row with no publication year
without recording it. Here each rule gives an ``exclusion_reason`` and the link
is published with ``status = excluded``.
"""

from __future__ import annotations

COMMENT_PREFIXES = ("comment on", "reply on", "reply to comment by", "final response", "author response")
REASONS = ("self-link", "comment", "peer-review", "conference-abstract", "gbif-download", "predates-data")

# EGU General Assembly abstracts are published on EGUsphere as 10.5194/egusphere-egu<year>-<n>.
# Other EGUsphere DOIs (10.5194/egusphere-<year>-<n>) are preprints and are counted like
# any other preprint. v3 excluded every DOI containing "egusphere" as an abstract.
EGU_ABSTRACT_PREFIX = "10.5194/egusphere-egu"


def _year(value) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def exclusion_reason(data_doi: str, citing_id: str, relation_class: str, work: dict | None,
                     dataset_year, tolerance_years: int = 2, use_classes=None) -> str | None:
    """The first rule the link breaks, or None if it is included."""
    from .relations import USE_CLASSES

    use_classes = USE_CLASSES if use_classes is None else use_classes
    work = work or {}
    if citing_id == data_doi:
        return "self-link"
    title = (work.get("title") or "").strip().lower()
    if title.startswith(COMMENT_PREFIXES):
        return "comment"
    if (work.get("work_type") or "").lower().startswith("peer-review"):
        return "peer-review"
    if citing_id.lower().startswith(EGU_ABSTRACT_PREFIX):
        return "conference-abstract"
    if citing_id.startswith("10.15468/"):
        return "gbif-download"
    if relation_class in use_classes:
        work_year, data_year = _year(work.get("issued")), _year(dataset_year)
        # A work can't use a dataset published long after it. A year either way is
        # normal (preprints, online-first, data deposited after acceptance), so
        # only a gap of `tolerance_years` or more is excluded.
        if work_year is not None and data_year is not None and data_year - work_year >= tolerance_years:
            return "predates-data"
    return None

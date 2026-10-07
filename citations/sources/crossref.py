"""Crossref data citations (beta endpoint): links Crossref members deposit between articles and datasets.

A source v3 did not use. On 7 Oct 2026 it returned 19 links for NGDC datasets
that v3 lacked, 13 of them for datasets with no v3 citation at all. The
endpoint is a beta: its relation names and paging may change, so unknown
relations are counted rather than guessed, and a failed DOI is retried next run.
"""

from __future__ import annotations

from ..harvest import RawLink, Tally, per_key
from ..ids import normalise_id
from ..relations import canonical, dataset_side, relation_class

SOURCE = "crossref"
DATACITATIONS_URL = "https://api.crossref.org/beta/datacitations/"

# Crossref's relation names, read with the article as subject and the dataset as object.
RELATIONS = {
    "references": "IsReferencedBy",
    "cites": "IsCitedBy",
    "based-on-data": "IsReferencedBy",
    "is_part_of": "IsSupplementTo",       # the dataset is part of the article's supplement
    "is-part-of": "IsSupplementTo",
    "is_supplemented_by": "IsSupplementTo",
    "is-supplemented-by": "IsSupplementTo",
    "has_supplement": "IsSupplementTo",
}


def map_relation(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in RELATIONS:
        return RELATIONS[key]
    return dataset_side(canonical(key), "object") if canonical(key) else None


def fetch_links(client, doi: str, mailto: str | None, tally: Tally) -> list[RawLink]:
    params = {"object-id": doi}
    if mailto:
        params["mailto"] = mailto
    url, links, seen_cursors, total = DATACITATIONS_URL, [], set(), None
    for _ in range(50):
        payload = client.get_json(url, params=params, allow_404=True)
        if payload is None:
            break
        message = payload.get("message") or {}
        total = message.get("total-results", total)
        for item in message.get("items") or []:
            subject, obj = item.get("subject") or {}, item.get("object") or {}
            s, o = normalise_id(subject.get("id")), normalise_id(obj.get("id"))
            other, work = (o, obj) if s and s[0] == doi else (s, subject)
            if not other or other[0] == doi:
                tally.add("no_identifier")
                continue
            relation = map_relation(item.get("relation"))
            if relation is None or relation_class(relation) is None:
                tally.add(f"unknown_relation:{item.get('relation')}")
                continue
            hint = {k: v for k, v in {"work_type": work.get("type"), "registration_agency": work.get("registration-agency"),
                                      "deposited": item.get("timestamp")}.items() if v}
            links.append(RawLink(doi, other[0], other[1], relation, item.get("relation") or "", "crossref", hint))
        nxt = message.get("next-page")
        if not nxt or nxt in seen_cursors or len(links) >= (total or 0):
            break
        seen_cursors.add(nxt)
        if str(nxt).startswith("http"):
            url, params = nxt, None
        else:
            params = {**params, "cursor": nxt} if params else {"object-id": doi, "cursor": nxt}
    if total and len(links) < total:
        tally.add("fewer_links_than_reported", int(total) - len(links))
    return links


def harvest(ctx, run_id: int) -> dict:
    tally = Tally()
    dois = [row["doi"] for row in ctx.datasets()]
    per_key(ctx, SOURCE, run_id, dois, lambda doi: fetch_links(ctx.client, doi, ctx.settings.mailto, tally))
    return {"details": tally.as_dict()}

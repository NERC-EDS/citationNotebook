"""Identifier normalisation, so the same work from two sources merges into one link."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from .config import NERC_PREFIX

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#]+", re.IGNORECASE)

# Values the old harvesters wrote into empty fields; never identifiers.
PLACEHOLDERS = {
    "", "not a doi", "info not given", "unknown repository", "unknown",
    "nan", "none", "null", "n/a", "error occurred", "api request failed",
}

_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_cid$|mc_eid$)", re.IGNORECASE)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    text = str(value).strip()
    return "" if text.lower() in PLACEHOLDERS else text


def extract_doi(value, exclude: str | None = None) -> str | None:
    """The DOI in `value` with its original case, or None.

    Handles bare DOIs, doi:/doi.org forms, publisher URLs with a DOI in the path
    (https://pubs.acs.org/doi/10.1021/...) and the doubled prefix some DataCite
    relations carry ("10.1016/10.1111/jbi.13501" -> "10.1111/jbi.13501").
    Query strings are ignored, and so is a DOI equal to `exclude`: a citing
    work's URL that mentions the cited dataset is not that dataset.
    """
    text = _text(value)
    if not text:
        return None
    if re.match(r"https?://", text, re.IGNORECASE):
        text = urlsplit(text).path
    text = unquote(text)
    matches = DOI_RE.findall(text)
    if not matches:
        return None
    doi = matches[0]
    inner = DOI_RE.findall(doi[3:])
    if inner and doi.split("/", 1)[1].startswith("10."):
        doi = inner[-1]
    # Trailing punctuation from surrounding text; ")" only when unbalanced.
    while True:
        stripped = doi.rstrip(".,;")
        if stripped.endswith(")") and stripped.count(")") > stripped.count("("):
            stripped = stripped[:-1]
        if stripped == doi:
            break
        doi = stripped
    if exclude and doi.lower() == str(exclude).strip().lower():
        return None
    return doi


def normalise_doi(value, exclude: str | None = None) -> str | None:
    """Bare lower-case DOI (DOIs are case-insensitive), or None."""
    doi = extract_doi(value, exclude)
    return doi.lower() if doi else None


def canonical_url(value) -> str | None:
    """A URL in one canonical form: lower-case scheme and host, no fragment,
    no tracking parameters, no trailing slash. None if `value` is not a URL."""
    text = _text(value)
    if not re.match(r"https?://", text, re.IGNORECASE):
        return None
    parts = urlsplit(text)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING.match(k)])
    path = parts.path.rstrip("/") if parts.path not in ("", "/") else ""
    return urlunsplit(("https", host, path, query, ""))


def normalise_id(value, scheme: str | None = None, exclude: str | None = None) -> tuple[str, str] | None:
    """(identifier, type) for a citing work, or None.

    A DOI anywhere in a URL path wins, so https://doi.org/10.1/x and 10.1/X
    become the same identifier. `scheme` is a hint from the source (Scholix
    IDScheme: doi, pmid, pmc, handle, url).
    """
    text = _text(value)
    if not text:
        return None
    scheme = (scheme or "").lower()
    if scheme in ("pmid", "pmc", "handle", "hdl"):
        kind = "handle" if scheme in ("handle", "hdl") else scheme
        bare = re.sub(r"^(pmid|pmc|hdl|handle):\s*", "", text, flags=re.IGNORECASE)
        bare = re.sub(r"^https?://(hdl\.handle\.net|identifiers\.org/[a-z]+)/", "", bare, flags=re.IGNORECASE)
        if kind == "pmc" and not bare.upper().startswith("PMC"):
            bare = "PMC" + bare
        return (f"{'hdl' if kind == 'handle' else kind}:{bare.strip()}", kind)
    doi = normalise_doi(text)
    if doi:
        if exclude and doi == str(exclude).strip().lower():
            return None  # the dataset itself, however it is written
        return (doi, "doi")
    url = canonical_url(text)
    if url:
        return (url, "url")
    return None


def link_id(data_doi: str, citing_id: str) -> str:
    """Stable id for a dataset x citing-work pair."""
    return hashlib.sha1(f"{data_doi}|{citing_id}".encode("utf-8")).hexdigest()


def is_nerc_dataset(citing_id: str | None) -> bool:
    return bool(citing_id) and citing_id.startswith(NERC_PREFIX)


def doi_url(doi: str) -> str:
    return f"https://doi.org/{doi}"

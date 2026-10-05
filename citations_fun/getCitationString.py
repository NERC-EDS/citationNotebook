"""Citation strings for the publications that cite NERC datasets.

For each row this produces `pub_citation_str`, which ends up as
`PubCitationStr` in Results/v3 and as `citationText` in the EDS citation API.

Order of preference for each row:
  1. A formatted citation from DOI content negotiation (only for real DOIs,
     only an HTTP 200 whose body isn't a known error message).
  2. The string from the previous run's results for the same publication,
     if that was a real citation (saves time, survives a formatter outage).
  3. A citation built from the row's own metadata (authors, year, title,
     publisher), so URL-identified works and formatter failures still get a
     readable string. Never a placeholder such as "not a doi" or an error
     message from the formatter.

The notebook used to ask for style "frontiers-of-biogeography", which the
formatters no longer have (doi.org answers {"code":"style-not-found",...});
"apa" works for Crossref and DataCite DOIs.

From late Feb 2026 every value in the results was an error message stored as
if it were a citation ("Unknown style frontiers-of-biogeography", "DOI exists
but metadata could not be retrieved ..."), because the response status and
body were never checked. The checks below, and the success-rate guard at the
end, are there so that can't happen silently again.
"""

import ast
import re
import time
from urllib.parse import unquote, urlsplit

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# DOI content negotiation: doi.org redirects to the registration agency
# (Crossref, DataCite, ...) which formats the citation with citeproc.
# https://citation.crosscite.org/docs.html
CONTENT_NEGOTIATION_URL = "https://doi.org/{doi}"

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#]+", re.IGNORECASE)

# Bodies the formatters return with errors (sometimes with HTTP 200).
# Kept specific: a broad "not found" could match a genuine title.
FORMATTER_ERRORS = re.compile(
    r"^unknown style|^doi not found|metadata could not be retrieved|"
    r"^resource not found|^too many requests|^service unavailable|"
    r"^internal server error|<html|<!doctype|"
    # Content negotiation reports errors as JSON, e.g.
    # {"code":"style-not-found","message":"Style [...] does not exist",...}
    r"^\s*[{\[]|style-not-found",
    re.IGNORECASE,
)

# Placeholders the harvesting steps write into empty fields.
PLACEHOLDERS = {
    "", "not a doi", "info not given", "unknown repository", "unknown",
    "nan", "none", "null", "n/a", "error occurred",
}


def _clean(value):
    """Text value, or '' for missing values and harvester placeholders."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in PLACEHOLDERS else text


def normalise_doi(value, data_doi=None):
    """The DOI in `value`, or None.

    Handles bare DOIs, doi:/doi.org forms, publisher URLs with a DOI in the
    path (https://pubs.acs.org/doi/10.1021/...) and the doubled prefix some
    DataCite relations carry ("10.1016/10.1111/jbi.13501" -> "10.1111/jbi.13501").
    Query strings are ignored, and so is a DOI equal to `data_doi`: a citing
    work's URL that mentions the cited dataset is not that dataset.
    """
    text = _clean(value)
    if not text:
        return None
    if re.match(r"https?://", text, re.IGNORECASE):
        text = urlsplit(text).path
    text = unquote(text)
    matches = DOI_RE.findall(text)
    if not matches:
        return None
    doi = matches[0]
    # Doubled prefix: the real DOI is the last "10.xxxx/..." in the string.
    inner = DOI_RE.findall(doi[3:])
    if inner and doi.split("/", 1)[1].startswith("10."):
        doi = inner[-1]
    doi = doi.rstrip(".,;)")
    if data_doi and doi.lower() == str(data_doi).strip().lower():
        return None
    return doi


def is_real_citation(text):
    """True for a usable citation string, False for errors and placeholders."""
    cleaned = _clean(text)
    return bool(cleaned) and len(cleaned) >= 20 and not FORMATTER_ERRORS.search(cleaned)


def _authors(value, limit=3):
    """'Family A., Family B., Family C., et al.' from the varied author formats."""
    text = _clean(value)
    if not text:
        return ""
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text
    names = []
    for item in parsed if isinstance(parsed, (list, tuple)) else [parsed]:
        if isinstance(item, (list, tuple)):
            parts = [_clean(p) for p in item if _clean(p)]
            if len(parts) >= 2:   # [given, family]
                given, family = parts[0], parts[-1]
                initials = "".join(f"{p[0]}." for p in re.split(r"[\s.\-]+", given) if p)
                names.append(f"{family} {initials}".strip())
            elif parts:           # [organisation]
                names.append(parts[0])
        elif _clean(item):
            names.append(_clean(item))
    if not names:
        return ""
    shown = ", ".join(names[:limit])
    return f"{shown}, et al." if len(names) > limit else shown


def _year(row):
    year = _clean(row.get("publicationYear"))
    if re.fullmatch(r"\d{4}(\.0)?", year):
        return year[:4]
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", _clean(row.get("pub_date")))
    return match.group(1) if match else ""


def fallback_citation(row, doi=None):
    """A plain citation from the row's metadata: Authors (Year). Title. Publisher. DOI."""
    authors = _authors(row.get("pub_authors"))
    year = _year(row)
    title = _clean(row.get("pub_title")).rstrip(".")
    publisher = _clean(row.get("pub_publisher")).rstrip(".")

    parts = []
    if authors:
        parts.append(f"{authors} ({year})." if year else f"{authors}.")
    elif year:
        parts.append(f"({year}).")
    if title:
        parts.append(f"{title}.")
    # Skip a publisher that repeats the title or an organisational author.
    if publisher and publisher.lower() not in title.lower() and publisher.lower() != authors.lower():
        parts.append(f"{publisher}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")
    # Without a title the string isn't worth showing; the widget falls back
    # to the URL itself.
    return " ".join(parts) if title else ""


def _session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,  # return the last response; status is checked below
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_formatted(session, doi, style, locale, timeout=15):
    """Formatted citation for `doi`, or None if the formatter didn't give one."""
    try:
        response = session.get(
            CONTENT_NEGOTIATION_URL.format(doi=doi),
            headers={
                "Accept": f"text/x-bibliography; style={style}; locale={locale}",
                "Accept-Charset": "utf-8",
            },
            timeout=timeout,
        )
    except requests.RequestException as error:
        print(f"{doi}: request failed ({error})")
        return None
    response.encoding = "utf-8"
    text = response.text.strip()
    if response.status_code != 200 or not is_real_citation(text):
        print(f"{doi}: no citation (HTTP {response.status_code}: {text[:80]!r})")
        return None
    return text


def get_citation_str(
    nerc_citations_df,
    previous_results=None,
    style="apa",
    locale="en-GB",
    min_success_rate=0.5,
    pause=0.1,
):
    """Add `pub_citation_str` to the dataframe and return it.

    previous_results: optional dataframe of last run's Results/v3 output
        (columns publication_doi, PubCitationStr). Real citations in it are
        reused instead of being fetched again.
    min_success_rate: if fewer than this share of the DOIs looked up this run
        get a formatted citation (and at least 20 were tried), raise instead of
        writing degraded results, so the scheduled run fails visibly. None
        disables the check.
    """
    reuse = {}
    if previous_results is not None and "PubCitationStr" in previous_results:
        for doi_value, text in zip(previous_results["publication_doi"], previous_results["PubCitationStr"]):
            doi = normalise_doi(doi_value)
            if doi and is_real_citation(text):
                reuse.setdefault(doi.lower(), text)
    print(f"Reusing {len(reuse)} citation strings from the previous results")

    session = _session()
    fetched = {}  # this run's lookups, so each DOI is fetched once
    stats = {"formatted": 0, "reused": 0, "fallback": 0, "empty": 0, "tried": 0, "succeeded": 0}
    strings = []

    for _, row in nerc_citations_df.iterrows():
        doi = normalise_doi(row.get("pub_doi"), row.get("data_doi"))
        text = None
        if doi:
            key = doi.lower()
            if key in reuse:
                text = reuse[key]
                stats["reused"] += 1
            else:
                if key not in fetched:
                    stats["tried"] += 1
                    fetched[key] = fetch_formatted(session, doi, style, locale)
                    stats["succeeded"] += fetched[key] is not None
                    time.sleep(pause)
                text = fetched[key]
                stats["formatted"] += text is not None
        if not text:
            text = fallback_citation(row, doi)
            stats["fallback" if text else "empty"] += 1
        strings.append(text)

    nerc_citations_df["pub_citation_str"] = strings
    print(f"Citation strings: {stats}")

    if min_success_rate is not None and stats["tried"] >= 20:
        rate = stats["succeeded"] / stats["tried"]
        if rate < min_success_rate:
            # The ::error:: prefix makes GitHub Actions annotate the run.
            message = (
                f"Only {stats['succeeded']} of {stats['tried']} DOIs ({rate:.0%}) got a formatted "
                f"citation from {CONTENT_NEGOTIATION_URL} with style={style}. The formatter is "
                "probably failing; not writing results."
            )
            print(f"::error::{message}")
            raise RuntimeError(message)

    return nerc_citations_df

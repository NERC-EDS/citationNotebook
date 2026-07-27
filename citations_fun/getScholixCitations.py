# Retrieve citation information from the OpenAIRE Scholexplorer v3 API.
#
# Migrated from v2 to v3 (https://api.scholexplorer.openaire.eu/v3/Links).
#
# Direction matters. Scholexplorer stores relationships on the *active side* of
# the verb ("A Cites B", never "B IsCitedBy A"). To find the works that cite a
# dataset, the dataset is the TARGET of the relationship and the citing work is
# the SOURCE -- so we query by `targetPid=<dataset DOI>` and read `source`.
# The previous v2 code queried `sourcePid` and kept only
# RelationshipType.Name == "IsReferencedBy"; under v3 the Name is "IsRelatedTo"
# (the semantic lives in SubType, e.g. "cites"), so that filter matched nothing
# and the wrong direction was queried -- dropping citations.
#
# Pagination is 0-indexed (responses report "currentPage": 0 for the first page).

import requests
import pandas as pd
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SCHOLIX_V3_BASE = "https://api.scholexplorer.openaire.eu/v3/Links"

# Column contract kept identical to the previous version so the downstream
# processScholixCitations / merge steps are unaffected.
COLUMN_NAMES = ["relation_type", "pub_title", "pub_date", "pub_authors",
                "pub_type", "pub_publisher", "pub_doi", "data_doi"]


def _first_doi(identifiers):
    """Return the first DOI from a Scholix Identifier list, else None."""
    for idinfo in identifiers or []:
        if idinfo.get("IDScheme") == "doi" and idinfo.get("ID"):
            return idinfo["ID"]
    return None


def getScholixCitations(dataCite_df, scholix_base=SCHOLIX_V3_BASE, relation=None,
                        subtypes=None, page_size=100, max_pages=1000, delay=0.2,
                        timeout=30):
    """
    For each dataset DOI in dataCite_df, fetch the works that cite/relate to it
    from Scholexplorer v3 and return them merged back onto dataCite_df.

    Parameters
    ----------
    relation : optional Scholix verb passed straight to the API (e.g. "Cites").
        Default None = fetch all incoming relations (do not pre-filter at the API).
    subtypes : optional iterable of RelationshipType SubType values to keep
        (compared lower-cased, e.g. {"cites", "references", "issupplementto"}).
        Default None = keep every incoming relation. The relation Name/SubType is
        always recorded in `relation_type` so downstream can filter later.
    """
    keep_subtypes = {s.lower() for s in subtypes} if subtypes else None

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    scholexInfo = []

    for doi in list(dataCite_df["data_doi"]):
        if not isinstance(doi, str) or not doi.strip():
            continue

        page = 0
        total_pages = 1  # updated from the first response
        while page < total_pages and page < max_pages:
            params = {"targetPid": doi, "page": page, "size": page_size}
            if relation:
                params["relation"] = relation
            try:
                r = session.get(scholix_base, params=params, timeout=timeout)
                if r.status_code != 200:
                    print(f"Status {r.status_code} for {doi} (page {page})")
                    break
                payload = r.json()
            except requests.RequestException as e:
                print(f"Request error for {doi} (page {page}): {e}")
                break
            except ValueError:
                print(f"Non-JSON response for {doi} (page {page})")
                break

            total_links = payload.get("totalLinks", 0) or 0
            total_pages = payload.get("totalPages", 0) or 0
            results = payload.get("result") or []
            # PID-scoped totals are reliable, but broad-query totals can come back
            # negative/garbage, so an empty page is the definitive stop signal.
            if total_links <= 0 or not results:
                break  # no (further) citations recorded for this dataset

            for link in results:
                # Per-record handling: one malformed link must not drop the page.
                try:
                    rel = link.get("RelationshipType") or {}
                    subtype = (rel.get("SubType") or "")
                    if keep_subtypes is not None and subtype.lower() not in keep_subtypes:
                        continue

                    source = link.get("source") or {}        # the citing work
                    publishers = source.get("Publisher") or []
                    rel_str = "/".join(x for x in (rel.get("Name"), rel.get("SubType")) if x)

                    scholexInfo.append([
                        rel_str,
                        source.get("Title"),
                        source.get("PublicationDate"),
                        source.get("Creator") or [],          # list of {name, ...}
                        source.get("Type"),
                        publishers[0].get("name") if publishers else None,
                        _first_doi(source.get("Identifier")),
                        doi,                                   # the dataset we queried
                    ])
                except Exception as e:
                    print(f"Skipping malformed record for {doi}: {e}")
                    continue

            page += 1
            if delay:
                time.sleep(delay)

    scholex_df = pd.DataFrame(scholexInfo, columns=COLUMN_NAMES)

    scholex_df_merged = scholex_df.merge(
        dataCite_df,
        on="data_doi",
        how="left",
    )

    print("Done!")
    return scholex_df_merged
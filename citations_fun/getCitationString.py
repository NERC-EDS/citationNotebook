import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout
from urllib3.util.retry import Retry
import time
import pandas as pd

def get_citation_str(nerc_citations_df):

    citationStrList = []  # create an empty list to store citation strings
    timeout_seconds = 10  # Define a timeout value for requests in seconds

    # Create a session with a custom adapter and retry configuration
    session = requests.Session()

    # Define a retry strategy with a backoff factor
    retry_strategy = Retry(
        total=5,  # Maximum number of retry attempts
        backoff_factor=5,  # Factor by which to multiply the sleep time between retries
        status_forcelist=[403, 429, 500, 502, 503, 504],  # HTTP status codes that trigger a retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)  # Apply the retry strategy
    session.mount('https://', adapter)

    for pubDOI in nerc_citations_df['pub_doi']:
        time.sleep(0.1)
        # Guard against non-string / missing DOIs (avoids AttributeError on NaN).
        if not isinstance(pubDOI, str) or not pubDOI.startswith('10.'):
            citationStrList.append('not a doi')
            continue

        print(pubDOI)
        result = None
        r = None  # reset every iteration so a failed request can't reuse a previous response
        try:
            r = session.get(("https://citation.doi.org/format?style=frontiers-of-biogeography&lang=en-GB&doi=" + pubDOI),
                            headers={"Accept": "text/x-bibliography", "Accept-Charset": "utf-8"}, timeout=timeout_seconds)
            print(r.status_code)
            # The formatter returns UTF-8. requests defaults to ISO-8859-1 for text/*
            # when the charset is absent, so force UTF-8 and read the text directly.
            # This replaces the old `r.text.encode('latin1').decode('utf-8')` round-trip,
            # which raised UnicodeEncodeError on any character outside latin1 (e.g. the
            # en-dash U+2013 used in page ranges like "1861-1875") -- issue #17.
            r.encoding = "utf-8"
            result = r.text
        except Timeout:
            print(f"Request for {pubDOI} timed out.")
        except ConnectionError as ce:
            print(f"A connection error occurred for {pubDOI}: {ce}")
        except Exception as e:
            print(f"An error occurred for {pubDOI}: {e}")
            if r is not None and r.text:
                r.encoding = "utf-8"
                result = r.text

        finally:
            citationStrList.append(result if result is not None else 'error occurred')

    nerc_citations_df['pub_citation_str'] = citationStrList # add the citation string list to df
    print('Done!')

    return nerc_citations_df
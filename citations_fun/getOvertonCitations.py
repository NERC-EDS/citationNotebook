# functions to harvest nerc dataset citations from Overton
import requests, time, json
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def overton_api_request(doi, session):
    url = "https://app.overton.io/documents.php"
    params ={
        "plain_dois_cited": doi,
        "format": "json",
        "api_key": "3c7b1a-849d90-77f9da",
    }
    r = session.get(url, params=params, timeout=30)
    print(r.status_code, "DOI: ", doi)
    r.raise_for_status()
    return r.json().get('results', [])


def getOvertonCitations(nerc_datacite_dois_df):

    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))


    results = []

    for doi in nerc_datacite_dois_df.data_doi:
        start = time.time()

        try:
            data = overton_api_request(doi, session)
            if data:
                results.append(data)
        except requests.RequestException as e:
            print(f"Error on {doi}: {e}")
            continue

        elapsed = time.time() - start
        # enforce at least 1s between requests
        if elapsed < 1:
            time.sleep(1.05 - elapsed)
        
    
    return results

def processOvertonResults(results):
    flat_results = [d for sublist in results for d in sublist]
    overton_df = pd.DataFrame(flat_results)
    # overton_df.to_csv("results/overton_list.csv", index= False )

    # extract columns we're interested in
    overton_df_sub = overton_df[['title', 'authors', 'published_on', 'document_url', 'highlights', 'source', 'overton_policy_document_series']]


    # extract relation type and data doi from highlights column dictionaries
    extracted_highlights = overton_df_sub["highlights"].apply(
        lambda x: {
            "type": x[0]["type"] if isinstance(x, list) and len(x) > 0 else None,
            "doi": x[0]["doi"] if isinstance(x, list) and len(x) > 0 else None,
        }
    )
    # Turn the Series of dicts into a DataFrame and join to the original
    extracted_highlights_df = pd.DataFrame(extracted_highlights.tolist())
    overton_df_sub = overton_df_sub.join(extracted_highlights_df)

    # extract title from source dictionary to get pub_publisher
    overton_df_sub["pub_publisher"] = overton_df_sub["source"].apply(
        lambda x: x.get("title") if isinstance(x, dict) else None
    )

    # drop highlights and source columns - no longer needed
    overton_df_sub = overton_df_sub.drop(['highlights', 'source'], axis = 1)

    # rename columns
    cols = {"title":"pub_title", 'authors':'pub_authors', 'published_on':'pub_date', 'document_url':'pub_doi', 'type':'relation_type', 'doi':'data_doi', 'overton_policy_document_series':'pub_type'}
    overton_df_sub = overton_df_sub.rename(columns = cols)

    # merge with nerc_datacite_dois_df before writing to latest_results_overton.csv
    with open("Results/intermediate_data/nerc_datacite_dois.json") as f:
        nerc_datacite_dois = json.load(f)
    nerc_datacite_dois_df = pd.DataFrame(nerc_datacite_dois)

    overton_df_merged = overton_df_sub.merge(
        nerc_datacite_dois_df,
        left_on='data_doi',
        right_on='data_doi',
        how='left'
    )

    overton_df_merged = overton_df_merged.drop(['data_page_number', 'data_self_link'], axis = 1)

    # add column source-id
    source_id = ['overton'] * len(overton_df_merged)
    overton_df_merged['source_id'] = source_id

    # re-oder columns
    overton_df_merged = overton_df_merged[[
        'data_doi', 'data_publisher', 'data_title', 'data_publication_year', 'data_authors',
        'relation_type', 'pub_doi', 'pub_title', 'pub_date', 'pub_authors', 'pub_type', 'pub_publisher', 'source_id'
    ]]

    # write to file
    overton_df_merged.to_csv("Results/intermediate_data/latest_results_overton.csv", index= False)

    return overton_df_merged


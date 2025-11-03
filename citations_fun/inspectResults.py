# functions for inspecting citations results

import pandas as pd


# view citations for a particular data_doi
def citations_one_doi(latest_results, doi):
    doi = "10.5285/2d0e4791-8e20-46a3-80e4-f5f6716025d2"
    result = latest_results[latest_results['data_doi'] == doi]
    print(result['data_title'].iloc[0])
    result = result[['relation_type_id', 
                    'publication_doi',
        'publication_title', # 'publication_date', 'publication_authors',
        'citation_event_source', 'pub_publisher', 
        #'publication_type'
        ]]

    with pd.option_context('display.max_colwidth', 400):
        display(result)



# code to compare results for a data doi - list the new pub_doi, the pub_dois that have gone, and the pub_dois that have remained the same

def compare_results_one_doi(latest_results, old_results, doi):
    latest_result = latest_results[latest_results['data_doi'] == doi].copy()
    old_result = old_results[old_results['data_doi'] == doi].copy()

    # latest_result['index'] = "latest"
    # old_result['index'] = "old"
    # combined_df = pd.concat([latest_result, old_result], ignore_index=True)
    # deduped_df = combined_df.drop_duplicates(subset=list(("data_doi", "publication_doi")), keep="first")
    # deduped_df[deduped_df['index'] == "old"]

    # sets of DOIs
    latest_dois = set(latest_result['publication_doi'])
    old_dois = set(old_result['publication_doi'])

    # compare
    new_dois = latest_dois - old_dois
    disappeared_dois = old_dois - latest_dois
    unchanged_dois = latest_dois & old_dois

    print(f"New DOIs: {len(new_dois)}")
    print(f"Disappeared DOIs: {len(disappeared_dois)}")
    print(f"Unchanged DOIs: {len(unchanged_dois)}")

    new_pubs = latest_result[latest_result['publication_doi'].isin(new_dois)][['publication_doi', 'publication_title']]
    disappeared_pubs = old_result[old_result['publication_doi'].isin(disappeared_dois) ][['publication_doi', 'publication_title']]
    unchanged_pubs = latest_result[latest_result['publication_doi'].isin(unchanged_dois)][['publication_doi', 'publication_title']]

    print("\nNew Publications:")
    with pd.option_context('display.max_colwidth', 400):
        display(new_pubs)

    print("\nDisappeared Publications:")
    with pd.option_context('display.max_colwidth', 400):
        display(disappeared_pubs)

    print("\nUnchanged Publications:")
    with pd.option_context('display.max_colwidth', 400):
        display(unchanged_pubs)


    summary = pd.concat([
        new_pubs.assign(status='new'),
        disappeared_pubs.assign(status='disappeared'),
        unchanged_pubs.assign(status='unchanged')
    ])

    with pd.option_context('display.max_colwidth', 400):
        display(summary.sort_values('status'))
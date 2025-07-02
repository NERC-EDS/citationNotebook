def getPublicationInfo(datacite_doi_events_df):
    import requests
    from requests.adapters import HTTPAdapter
    import pandas as pd
    from urllib3.util.retry import Retry
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Set up a session with automatic retries.
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)


# work in the gpt suggestion from here def fetch_pub_info(item):
    #     pubdoi = item['subj-id']
    #     result = {
    #         'pub_doi_url': pubdoi,
    #         'pub_Title': "Info not given",
    #         'pub_authors': "Info not given",
    #         'publisher': "Info not given",
    #         'pub_type': "Info not given",
    #         'pub_date': "Info not given",
    #     }
    #     if pubdoi.startswith('https://doi.org/'):
    #         try:
    #             r = session.get(pubdoi, headers={"Accept": "application/json"})
    #             # You can log or print status here if desired
    #             # Process the JSON response.
    #             data = r.json()
    #             result['pub_Title'] = data.get('title', "Info not given")
                
    #             authors = []
    #             for author in data.get('author', []):
    #                 # Safely getting 'given' and 'family'
    #                 given = author.get('given', '')
    #                 family = author.get('family', '')
    #                 authors.append([given, family])
    #             result['pub_authors'] = authors if authors else "Info not given"
                
    #             # 'publisher' might come from a different key depending on the API specification.
    #             result['publisher'] = data.get('type', "Info not given")
    #             result['pub_type'] = data.get('type', "Info not given")
                
    #             # Try multiple keys for publication date.
    #             result['pub_date'] = data.get('created', {}).get('date-parts') or data.get('created') or data.get('published', "Info not given")
    #         except Exception as e:
    #             # You might want to log the exception for debugging.
    #             pass
    #     else:
    #         result['pub_Title'] = "not a doi"
    #         result['pub_authors'] = "not a doi"
    #         result['publisher'] = "not a doi"
    #         result['pub_type'] = "not a doi"
    #     return result

    # # Use ThreadPoolExecutor to speed up fetching.
    # pub_info = []
    # with ThreadPoolExecutor(max_workers=10) as executor:
    #     futures = [executor.submit(fetch_pub_info, item) for item in datacite_json]
    #     for count, future in enumerate(as_completed(futures)):
    #         pub_info.append(future.result())
    #         # Optionally log progress
    #         print(f"Processed {count + 1}/{len(datacite_json)}")

    # pubInfo_df = pd.DataFrame(pub_info)
    # print("Done!")
    # return pubInfo_df

    
    pub_info = []
    for count, pubdoi in enumerate(datacite_doi_events_df['pub_doi_url']):
        #if not a doi.org - skip?

        if pubdoi.startswith('https://doi.org/'):
            r = requests.get(pubdoi, headers={"Accept": "application/json"}) 
            print(count, pubdoi, r.status_code)
    #         except:
    #             title = "API request failed"
    #             authors = "API request failed"
    #             publisher = "API request failed"

    #             pub_info.append({
    #                 'pub_doi': pubdoi,
    #                 'pub_Title': title,
    #                 'pub_authors': authors,
    #                 'publisher': publisher
    #             # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
    #             })
    #             continue


            try:
                title = r.json()['title']
            except:
                title = "Info not given"

            try:           
                authors = []
                for jj in range(len(r.json()['author'])):
                    authors.append([r.json()['author'][jj]['given'],r.json()['author'][jj]['family']])
            except:
                authors = "Info not given"

            try:
                publisher = r.json()['type'] # was ['publisher']
            except:
                publisher = "Info not given"
                
            try:
                pub_type = r.json()['type']
            except:
                pub_type = "Info not given"
                
            try:
                pub_date = r.json()['created']['date-parts']
            except:
                try:
                    pub_date = r.json()['created']
                except:
                    try:
                        pub_date = r.json()['published']
                    except:
                        pub_date = "Info not given"

            pub_info.append({
                    'pub_doi_url': pubdoi,
                    'pub_Title': title,
                    'pub_authors': authors,
                    'pub_publisher': publisher,
                    'pub_type': pub_type,
                    'pub_date': pub_date
                
                # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
            })

            time.sleep(0.1) # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
            if count % 100 == 0: # if count is a multiple of 10 wait for a bit longer
                time.sleep(30)
        else:
            title = "not a doi"
            authors = "not a doi"
            publisher = "not a doi"
            pub_type = "not a doi"
            pub_date = "Info not given"
            pub_info.append({
                    'pub_doi_url': pubdoi,
                    'pub_Title': title,
                    'pub_authors': authors,
                    'pub_publisher': publisher,
                    'pub_type': pub_type,
                    'pub_date': pub_date
                # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
                })


    # add new publication info columns to dataframe
    datacite_doi_events_pubInfo_df = pd.DataFrame(pub_info)

    # # for json input
    # datacite_json_pubInfo = datacite_json
    # for col in pubInfo_df.columns[1:]:
    # # create dictionary of doi, value pairs 
    #     mapping = pubInfo_df.set_index('pub_doi_url')[col].to_dict()

    #     for record in datacite_json_pubInfo:
    #         doi = record.get('subj-id')
    #         record[col] = mapping.get(doi, None)

    #         record['subj-id'] = doi.replace('https://doi.org/', '')

    # for df input
    # loop through new columns to be added to df
    # for ii in datacite_doi_events_pubInfo_df.columns[1:]:
    #     # create dictionary of doi, value pairs 
    #     d = datacite_doi_events_pubInfo_df.set_index('pub_doi_url')[ii].to_dict()

    #     # use the doi to map the dictionary to datacite_doi_events_df
    #     datacite_doi_events_pubInfo_df.loc[:,ii] = datacite_doi_events_pubInfo_df.subj_id.map(d)

    merged_df = datacite_doi_events_df.merge(
        datacite_doi_events_pubInfo_df,
        on='pub_doi_url',
        how='left',  # or 'inner' if you want to keep only matched rows
        suffixes=('', '_pubInfo')  # to disambiguate duplicate column names like 'publisher'
    )



    

    print("Done!")
    # return datacite_json_pubInfo
    # return crossRef_df_gbif_filtered2_deduplicated
    return merged_df

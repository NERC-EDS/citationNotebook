def getPublicationInfo(datacite_doi_events_df):
    import requests
    from requests.adapters import HTTPAdapter
    from requests.exceptions import RequestException
    import pandas as pd
    from urllib3.util.retry import Retry
    import time

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

    
    pub_info = []
    for count, pubdoi in enumerate(datacite_doi_events_df['pub_doi']):
        
        #if not a doi.org - skip?
        if pubdoi.startswith('https://doi.org/'):

            try: 
                r = session.get(pubdoi, headers={"Accept": "application/json"})
                print(count, pubdoi, r.status_code)
            except RequestException as e:
                print(f"[Error] Failed to fetch {pubdoi}: {e}")
                title = "API request failed"
                pub_date = "API request failed"
                authors = "API request failed"
                publisher = "API request failed"
                pub_type = "API request failed"

                pub_info.append({
                    'pub_doi': pubdoi,
                    'pub_title': title,
                    'pub_date': pub_date,
                    'pub_authors': authors,
                    'pub_publisher': publisher,
                    'pub_type': pub_type
                })
                continue

            try:
                data = r.json()
            except ValueError:
                data = {}


            try:
                title = data['title']
            except:
                title = "Info not given"

            try:           
                authors = []
                for jj in range(len(data['author'])):
                    authors.append([data['author'][jj]['given'],data['author'][jj]['family']])
            except:
                try: # try just getting the string for info
                    authors = data['author']
                except:
                    authors = "Info not given"

            try:
                publisher = data['type'] # was ['publisher']
            except:
                publisher = "Info not given"
                
            try:
                pub_type = data['type']
            except:
                pub_type = "Info not given"
                
            try:
                pub_date = data['created']['date-parts']
            except:
                try:
                    pub_date = data['created']
                except:
                    try:
                        pub_date = data['published']
                    except:
                        pub_date = "Info not given"
            
            # format pub_date when its given as nested list [[]]
            try:
                pub_date_format  = f"{pub_date[0][2]}/{pub_date[0][1]}/{pub_date[0][0]}"
            except:
                pub_date_format = pub_date

                

            pub_info.append({
                    'pub_doi': pubdoi,
                    'pub_title': title,
                    'pub_date': pub_date_format,
                    'pub_authors': authors,
                    'pub_publisher': publisher,
                    'pub_type': pub_type
            })

            time.sleep(0.1) # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
            if count != 0 and count % 500 == 0: # if count is a multiple of 10 wait for a bit longer
                time.sleep(30)
        else:
            title = "not a doi"
            authors = "not a doi"
            publisher = "not a doi"
            pub_type = "not a doi"
            pub_date = "Info not given"
            pub_info.append({
                    'pub_doi': pubdoi,
                    'pub_title': title,
                    'pub_date': pub_date,
                    'pub_authors': authors,
                    'pub_publisher': publisher,
                    'pub_type': pub_type
                })


    # add new publication info columns to dataframe
    datacite_doi_events_pubInfo_df = pd.DataFrame(pub_info)

    merged_df = datacite_doi_events_df.merge(
        datacite_doi_events_pubInfo_df,
        on='pub_doi',
        how='left', 
        suffixes=('', '_pubInfo')  # to disambiguate duplicate column names like 'publisher'
    )

    # remove leading url bit from pub_doi if present
    merged_df['pub_doi'] = merged_df['pub_doi'].str.replace(
        'https://doi.org/', '', regex=False
    )


    print("Done!")

    return merged_df

def getPublicationInfo(crossRef_df_gbif_filtered2_deduplicated):
    import requests
    from requests.adapters import HTTPAdapter
    import pandas as pd
    from urllib3.util.retry import Retry
    import time
    
    pub_info = []
    for count, pubdoi in enumerate(crossRef_df_gbif_filtered2_deduplicated['subj_id']):
        #if not a doi.org - skip?
        if pubdoi.startswith('https://doi.org/'):
            r = requests.get(pubdoi, headers={"Accept": "application/json"}) 
            print(pubdoi, r.status_code)
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
                    'publisher': publisher,
                    'pub_type': pub_type,
                    'pub_date': pub_date
                
                # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
            })

            time.sleep(1.1) # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
            if count % 30 == 0: # if count is a multiple of 10 wait for a bit longer
                time.sleep(180)
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
                    'publisher': publisher,
                    'pub_type': pub_type,
                    'pub_date': pub_date
                # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
                })


    # add new publication info columns to dataframe
    pubInfo_df = pd.DataFrame(pub_info)

    # loop through new columns to be added to df
    for ii in pubInfo_df.columns[1:]:
        # create dictionary of doi, value pairs 
        d = pubInfo_df.set_index('pub_doi_url')[ii].to_dict()

        # use the doi to map the dictionary to crossRef_df_gbif_filtered2_deduplicated
        crossRef_df_gbif_filtered2_deduplicated.loc[:,ii] = crossRef_df_gbif_filtered2_deduplicated.subj_id.map(d)

    print("Done!")
    return crossRef_df_gbif_filtered2_deduplicated

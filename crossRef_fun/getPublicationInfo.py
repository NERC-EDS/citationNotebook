def getPublicationInfo(crossRef_df_gbif_filtered2_deduplicated):
    import requests
    from requests.adapters import HTTPAdapter
    import pandas as pd
    from urllib3.util.retry import Retry

    s = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=3)
    
    adapter = HTTPAdapter(max_retries=retries)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    
    pub_info = []
    for pubdoi in crossRef_df_gbif_filtered2_deduplicated['subj_id']:
        print(pubdoi)
        try:
            r = s.get(pubdoi, headers={"Accept": "application/json"}) 
        except:
            title = "API request failed"
            authors = "API request failed"
            publisher = "API request failed"
            pub_date = "API request failed"
            
            pub_info.append({
                'pub_doi': pubdoi,
                'pub_Title': title,
                'pub_authors': authors,
                'publisher': publisher,
                'pub_date': pub_date
                
            # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
            })
            continue
            

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
            publisher = r.json()['publisher']
        except:
            publisher = "Info not given"
            
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
                'pub_doi': pubdoi,
                'pub_Title': title,
                'pub_authors': authors,
                'publisher': publisher,
                'pub_date': pub_date
            # add publication date to this - in order to check if this is before the dataset publication date - could be a way to filter out dodgy results
        })


    # add new publication info columns to dataframe
    pubInfo_df = pd.DataFrame(pub_info)

    # loop through new columns to be added to df
    for ii in pubInfo_df.columns[1:]:
        # create dictionary of doi, value pairs 
        d = pubInfo_df.set_index('pub_doi')[ii].to_dict()

        # use the doi to map the dictionary to crossRef_df_gbif_filtered2_deduplicated
        crossRef_df_gbif_filtered2_deduplicated.loc[:,ii] = crossRef_df_gbif_filtered2_deduplicated.subj_id.map(d)

    print("Done!")
    return crossRef_df_gbif_filtered2_deduplicated

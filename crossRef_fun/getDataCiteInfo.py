# Pass citation info to datacite API to collect relevant info on the datasets, data centres etc

# crossRef_df should contain columns 'obj_id' and 'subj_id' which contain the NERC data DOIs and the DOIs of the publications that have cited them, respectively.
# currently it is written with 'obj_id' and 'subj_id' given as the full url e.g. https://doi.org/10.5285/17bebd7e-d342-49fd-b631-841ff148ecb0

def getDataCiteInfo(crossRef_df):
    import pandas as pd
    import requests
    import json
    
    dups = crossRef_df.duplicated('obj_id')
    crossRef_df_indivDatasets = crossRef_df.drop(crossRef_df[dups].index)

    # Define the DataCite REST API URL
    url = 'https://api.datacite.org/dois/10.5285/'

    # Create an empty list to store the results
    results = []
    errors = []

    # Loop through each dataset DOI in  citationInfo and retrieve the metadata
    for data_doi, pub_doi in zip(crossRef_df_indivDatasets['obj_id'], crossRef_df_indivDatasets['subj_id'],):
        print(data_doi, pub_doi)
        doi_url = url + data_doi.split('/')[4] # need to get everything after last /
        response = requests.get(doi_url)
        print('API response: ', response.status_code)
        if response.status_code == 200:
            metadata = json.loads(response.content.decode('utf-8'))

            # Extract the title, author list, and publication date from the metadata
            try:           
                title = metadata['data']['attributes']['titles'][0]['title']
            except:
                title = "Info not given"

            try:           
                authors = []
                for jj in range(len(metadata['data']['attributes']['creators'])):
                    authors.append(metadata['data']['attributes']['creators'][jj]['name'])
            except:
                authors = "Info not given"

            try:           
                publisher = metadata['data']['attributes']['publisher']
            except:
                publisher = "Info not given"

            try:           
                date = metadata['data']['attributes']['dates'][0]['date']
            except:
                date = "Info not given"

            try:           
                date_type =  metadata['data']['attributes']['dates'][0]['dateType']
            except:
                date_type = "Info not given"

            try:           
                citation_count = metadata['data']['attributes']['citationCount']
            except:
                citation_count = "Info not given"

            try:           
                relatedIdentifiers_list = metadata['data']['attributes']['relatedIdentifiers']
            except:
                relatedIdentifiers_list = "Info not given"

            try:           
                citation_list = metadata['data']['relationships']['citations']['data']
            except:
                citation_list = "Info not given"   

            # Add the metadata to the results list
            results.append({
                'dataset_DOI': data_doi,
                'dataset_Title': title,
                'dataset_authors': authors,
                'dataset_publisher': publisher,
                'dataset_date': date,
                'dataset_date_Type': date_type,
                'related_identifiers_list': relatedIdentifiers_list,
                'DataCite_Citation_count': citation_count,
                'DataCite_Citations_list': citation_list
            })

        else:
            errors.append({
                'Dataset_DOI': data_doi,
                'Publication_DOI': pub_doi,
                'reason': "Data DOI error"
            })

    # Convert the results list to a Pandas DataFrame
    dataCite_df = pd.DataFrame(results)
    print('Data Retrieved!')
    
    # add section formatting the publisher names - write as function
    newPublisherLst = []
    for dataCentreName in dataCite_df['dataset_publisher']:
        if type(dataCentreName) == float or dataCentreName is None:
            newPublisherLst.append(dataCentreName)
            continue
        else:
            pass

        dataCentreName_lower = dataCentreName.lower() # make it all lowercase as 'in' operator used below is case sensitive
        if 'polar' in dataCentreName_lower:
            newPublisherLst.append('Polar Data Centre (PDC)')
        elif 'atmospheric' in dataCentreName_lower or 'badc' in dataCentreName_lower or 'earth' in dataCentreName_lower:
            newPublisherLst.append('Centre for Environmental Data Analysis (CEDA)')
        elif 'oceanographic' in dataCentreName_lower:
            newPublisherLst.append('British Oceanographic Data Centre (BODC)')
        elif 'geological' in dataCentreName_lower or 'geoscience' in dataCentreName_lower:
            newPublisherLst.append('National Geoscience Data Centre (NGDC)')
        elif 'environmental information' in dataCentreName_lower:
            newPublisherLst.append('Environmental Information Data Centre (EIDC)')
        elif 'environmental data' in dataCentreName_lower:
            newPublisherLst.append('Centre for Environmental Data Analysis (CEDA)')
        else:
            newPublisherLst.append(dataCentreName)
    dataCite_df['dataset_publisher_processed'] = newPublisherLst
    dataCite_df = dataCite_df.drop(['dataset_publisher'], axis=1)
    
    print('Data Centre names processed!')
    
    return errors, dataCite_df
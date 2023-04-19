# function to process the citation results from getScholixDatasetCitations

def process_citation_results(dataCite_df, scholex_df):
    import pandas as pd
# removed as no longer counting citations before this stage    
#     #### Add the citation count collected from Scholex for each dataset to the DataCite dataframe
#     #create dictionary of dataset DOIs and citations for that DOI from scholex_df
#     d = scholex_df.set_index('datasetDOI')['citations'].to_dict()

#     # map that dictionary of DOI - citation pairs to the DOIs in  dataCite_df
#     dataCite_df['citations'] = dataCite_df.datasetDOI_attribute.map(d)

#     #convert nans to 0 and floats to intergers
#     dataCite_df['citations'] = dataCite_df['citations'].fillna(0)
#     dataCite_df['citations'] = dataCite_df['citations'].astype('int')
    
    
    #### Process dataframes and tidy up some columns
    # DataCite_df - process publisher names to result in one consistent name for each data centre
    # this may need reviewing periodically as it may not catch every variation of data centre names
    newPublisherLst = []
    for dataCentreName in dataCite_df['publisher']:
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
    dataCite_df['publisher_processed'] = newPublisherLst

    #  scholex_df - process publisher names to result in one consistent name for each data centre
    # this may need reviewing periodically as it may not catch every variation of data centre names
    newPublisherLst = []
    for dataCentreName in scholex_df['datasetPublisher']:
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
    scholex_df['publisher_processed'] = newPublisherLst
    
    
    #  dataCite_df - re-order and rename old publisher column
    dataCite_df = dataCite_df[['publisher_processed', 'title',  'creators', 'datasetDOI_attribute', 'dates', 'page_number',
           'Page endpoint']]
    dataCite_df = dataCite_df.rename({'publisher_processed': 'publisher'}, axis=1)

    # scholex_df - remove old publisher column and rename new one
    scholex_df = scholex_df.drop(['datasetPublisher'], axis=1)
    scholex_df = scholex_df.rename({'publisher_processed': 'datasetPublisher'}, axis=1)
    
    return dataCite_df, scholex_df
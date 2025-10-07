# function to process the citation results from getScholixDatasetCitations

def process_citation_results(scholex_df):

    # filter out gbif registrant code prefix 10.15468
    # scholex_df = scholex_df[~scholex_df.pubID.str.contains("10.15468")]
    scholex_df = scholex_df[~scholex_df['pub_doi'].apply(lambda x: str(x)).str.contains("10.15468")]

    #  scholex_df - process publisher names to result in one consistent name for each data centre
    # this may need reviewing periodically as it may not catch every variation of data centre names
    newPublisherLst = []
    for dataCentreName in scholex_df['data_publisher']:
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
    
    # scholex_df - remove old publisher column and rename new one
    scholex_df = scholex_df.drop(['data_publisher'], axis=1)
    scholex_df['data_publisher'] = newPublisherLst

    # remove leading url bit from pub_doi if present
    scholex_df['pub_doi'] = scholex_df['pub_doi'].str.replace(
        'https://doi.org/', '', regex=False
    )

    # process pub authors
    pub_authors_processed = []
    for authorList in scholex_df['pub_authors']:
        pubAuthorList = []
        for individual in authorList:
            name = individual['name']
            pubAuthorList.append(name)
        pub_authors_processed.append(pubAuthorList)

    scholex_df = scholex_df.drop(['pub_authors'], axis = 1)
    scholex_df['pub_authors'] = pub_authors_processed
    

    # rename columns
    # scholex_df.rename({'old name': 'new name'}, axis=1)



# scholex_df.columns
#     ['relationshipType', 'pubTitle', 'pubDate', 'pubAuthors', 'pubID',
#        'datasetDOI', 'datasetPublisher', 'datasetTitle', 'datasetAuthors']

# scholex_df_processed.columns
# ['relationshipType', 'pubTitle', 'pubDate', 'pubID', 'datasetDOI',
#        'datasetTitle', 'datasetAuthors', 'datasetPublisher',
#        'pubAuthors_processed']

# ideal columns
# ['data_doi', 'data_publisher', 'data_title', 'data_dates', 'data_publication_year', 'data_authors', 'data_registered', 'relation_type', 'pub_doi', 'pub_title', 'pub_date', 'pub_authors']


    # add column source-id
    source_id = ['scholex'] * len(scholex_df)
    scholex_df['source_id'] = source_id

    scholex_df_drop = scholex_df.drop(['data_page_number', 'data_self_link'], axis=1)

    scholex_df_drop_names = scholex_df_drop[[
        'data_doi', 'data_publisher', 'data_title', 'data_publication_year', 'data_authors',
        'relation_type', 'pub_doi', 'pub_title', 'pub_date', 'pub_authors', "pub_type", "pub_publisher", 'source_id'
    ]]   

    scholex_df_drop_names.to_csv("results/latest_results_scholex.csv", index= False )
    
    return scholex_df_drop_names
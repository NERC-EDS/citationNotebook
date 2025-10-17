def process_dataset_publisher_names(datacite_doi_events_df):

    #process dataset publisher names
    newPublisherLst = []
    for dataCentreName in datacite_doi_events_df['publisher']:
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
    datacite_doi_events_df['publisher_processed'] = newPublisherLst

    datacite_doi_events_df = datacite_doi_events_df.drop(['publisher'], axis=1)
    datacite_doi_events_df = datacite_doi_events_df.rename(columns={'publisher_processed':'data_publisher'})

    return datacite_doi_events_df
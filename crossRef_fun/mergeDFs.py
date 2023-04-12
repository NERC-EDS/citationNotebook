# merge crossRef_df and dataCite_df to get dataset info in crossref_df and to create new dataset focussed df
def mergeDFs(dataCite_df, crossRef_df_gbif_filtered2_deduplicated):
    # for each column create a mapping pair of dataset DOI and that column name, but skips first column 'Dataset_DOI' in loop
    for ii in dataCite_df.columns[1:]: # 

        # create dictionary of data_doi, value pairs 
        d = dataCite_df.set_index('dataset_DOI')[ii].to_dict()

        # use the data doi to map the dictionary to the crossref_df
        crossRef_df_gbif_filtered2_deduplicated.loc[:,ii] = crossRef_df_gbif_filtered2_deduplicated.obj_id.map(d)


    # create data frame that just lists each dataset and has citations counts from crossref, scholex, datacite etc
    # remove rows from crossref with duplicated obj_id
    dups = crossRef_df_gbif_filtered2_deduplicated.duplicated('obj_id')
    dataset_df = crossRef_df_gbif_filtered2_deduplicated.drop(crossRef_df_gbif_filtered2_deduplicated[dups].index)
    dataset_df = dataset_df.drop(['relation_type_id', 'source_id', 'subj_id', 'subj_work_type_id'], axis = 1) # 'subj_work_type_id'

    # count how many times each dataset DOI appears in crossRef_df_processed and add this number to dataset_df
    crossRef_citation_counts = crossRef_df_gbif_filtered2_deduplicated['obj_id'].value_counts()

    # need counts that include or exclude different relation_type_ids and subj_work_type_id

    # create dictionary of data_doi, crossRef_citation_counts 
    d = crossRef_citation_counts.to_dict()

    # use the data doi to map the dictionary to the dataset_df
    dataset_df['crossRef_citation_count'] = dataset_df.obj_id.map(d)
    
    return dataset_df, crossRef_df_gbif_filtered2_deduplicated

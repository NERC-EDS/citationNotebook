# filter and process the results
def filterCrossRefResults(results_folder_path_name):
    from crossRef_fun.eventRecord import eventRecord
    import os
    import pandas as pd
    
    # instance of a class to interpret the events
    jd1 = eventRecord()

    # get all the filenames
    files = os.listdir(results_folder_path_name)

    # load the json event data from multiple files
    jd1.mergeJsons(files, folder = results_folder_path_name)

    ## filter out twitter wikipedia etc - later add options to include these info
    filters = {"source_id" : ['twitter', 'wikipedia', 'newsfeed', 'wordpressdotcom', 'reddit-links']}
    filtered_info = jd1.filter(filters, mode = 'NOT')

    # collect relevant citation info for NERC project
    citationInfo = filtered_info.collectCitationInfo()

    # convert to dataframe
    crossRef_df = pd.DataFrame(citationInfo)

    # filter out gbif registrant code prefix 10.15468
    crossRef_df_gbif_filtered = crossRef_df[~crossRef_df.subj_id.str.contains("10.15468")]

    # filter out relationship_type_id values that we don't want - these all need examining more closely
    crossRef_df_gbif_filtered2 = crossRef_df_gbif_filtered[~crossRef_df_gbif_filtered.relation_type_id.str.contains("is_referenced_by|discusses|is_new_version_of|is_supplemented_by|is_previous_version_of")]

    # remove duplicate subj_ids for each obj_id - e.g. 10.5285/a7f28dea-64f7-43b5-bc39-a6cfcdeefbda has multiple references from 10.5285/65140444-b5fa-4a5e-9ab4-e86c106051e2
    # find rows where obj_id and subj_id are the same - should I match any other columns?
    dups = crossRef_df_gbif_filtered2.duplicated(subset=['obj_id', 'subj_id'])
    crossRef_df_gbif_filtered2_deduplicated = crossRef_df_gbif_filtered2.drop(crossRef_df_gbif_filtered2[dups].index)
    
    return crossRef_df_gbif_filtered2_deduplicated

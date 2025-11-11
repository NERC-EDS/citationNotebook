import pandas as pd


def filterCitations(nerc_citations_df):


    # comments on pre-prints, begin with: "Comment on" "Reply on" "Reply to comment by" "final response"
    pub_title_filter_list = ("Comment on", "Reply on", "Reply to comment by", "final response")
    filtered_out_df = nerc_citations_df[nerc_citations_df['pub_title'].str.startswith(pub_title_filter_list)]
    nerc_citations_df_filtered = nerc_citations_df[~nerc_citations_df['pub_title'].str.startswith(pub_title_filter_list)]


    # publication.types ="peer-review"
    pub_type_filter_list = ("peer-review")
    filtered_out_df = nerc_citations_df[nerc_citations_df['pub_type'].str.startswith(pub_type_filter_list)]
    nerc_citations_df_filtered = nerc_citations_df[~nerc_citations_df['pub_type'].str.startswith(pub_type_filter_list)]


    # if pub_doi contians:
    # "egusphere" - always a conference abstract
    # "10.15468" - gbif dataset downloads
    # define list of strings to look for and join with or | statements
    pub_doi_filter_list = ("egusphere", "10.15468")
    pattern = "|".join(pub_doi_filter_list)
    result = nerc_citations_df_filtered[nerc_citations_df_filtered['pub_doi'].str.contains(pattern, na=False)]
    filtered_out_df = pd.concat([filtered_out_df, result], ignore_index=True)
    nerc_citations_df_filtered = nerc_citations_df_filtered[~nerc_citations_df_filtered['pub_doi'].str.contains(pattern, na=False)]

    

    return (nerc_citations_df_filtered, filtered_out_df)
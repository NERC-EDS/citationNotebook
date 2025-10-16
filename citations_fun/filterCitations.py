import pandas as pd


def filterCitations(nerc_citations_df):


    # comments on pre-prints, begin with: "Comment on" "Reply on" "Reply to comment by" "final response"
    pub_title_filter_list = ("Comment on", "Reply on", "Reply to comment by", "final response")
    filtered_out_df = nerc_citations_df[nerc_citations_df['pub_title'].str.startswith(pub_title_filter_list)]
    nerc_citations_df_filtered = nerc_citations_df[~nerc_citations_df['pub_title'].str.startswith(pub_title_filter_list)]


    # # code to filter out things like if pub_doi contians "egusphere" etc? - always a conference abstract
    pub_doi_filter_list = ("egusphere")
    result = nerc_citations_df_filtered[nerc_citations_df_filtered['pub_doi'].str.contains(pub_doi_filter_list)]
    filtered_out_df = pd.concat([filtered_out_df, result], ignore_index=True)
    nerc_citations_df_filtered = nerc_citations_df_filtered[~nerc_citations_df_filtered['pub_doi'].str.contains(pub_doi_filter_list)]



    return (nerc_citations_df_filtered, filtered_out_df)
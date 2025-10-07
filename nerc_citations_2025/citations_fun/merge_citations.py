# function to merge citations from multiple sources

# df_list = [dataCite_df, scholex_df, overton_df] # list of dataframes to merge

def merge_citation_dfs(df_list):

    combined_df = pd.concat(df_list, ignore_index=True)

    deduped_df = combined_df.drop_duplicates(subset=list(("data_doi", "pub_doi")), keep="first")

    return deduped_df
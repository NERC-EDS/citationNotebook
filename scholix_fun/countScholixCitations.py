### Count citations by counting occurrences of each dataset in scholex_df

def countScholixCitations(scholex_df):
    import pandas as pd
    # Count occurrence of each dataset in scholex_df
    dups_dataset = scholex_df.pivot_table(columns=['datasetDOI'], aggfunc='size')
    dups_dataset_df = pd.DataFrame({'datasetDOI':dups_dataset.index, 'citations':dups_dataset.values})

    #create dictionary of dataset DOIs and citations for that DOI from scholex_df
    d = dups_dataset_df.set_index('datasetDOI')['citations'].to_dict()

    # map that dictionary of DOI - citation pairs to the datasetDOIs in  scholex_df
    scholex_df['citations_count'] = scholex_df.datasetDOI.map(d)
    
    return scholex_df
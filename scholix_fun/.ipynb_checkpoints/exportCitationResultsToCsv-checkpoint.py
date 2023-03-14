
def exportCitationResultsToCsv(scholex_df, dataCite_df, fp):
    from datetime import date
    import pandas as pd
    
    today = date.today()

    scholex_filename = fp + 'dataset_citation_publication_info_' + (today.strftime("%d%m%Y")) + '.csv'
    scholex_df.to_csv(scholex_filename, index = False)
    print(scholex_filename)

    dataset_filename = fp + 'dataset_citation_counts_' + (today.strftime("%d%m%Y")) + '.csv'
    dataCite_df.to_csv(dataset_filename, index = False)
    print(dataset_filename)
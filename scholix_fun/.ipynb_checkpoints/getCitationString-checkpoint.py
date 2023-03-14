### Get the citation string (APA format) of the publication that has cited the dataset

# TAKES A LONG TIME - ~90-120 MINS - can skip this if you don't want this info
def getCitationString(scholex_df):
    import requests
    import pandas as pd
    citationStrList = [] # create an empty list in which to put the citation strings

    for pubDOI in scholex_df['pubID']:

        r = requests.get(('https://doi.org/' + pubDOI), headers={"Accept": "text/x-bibliography", "style": "apa"})
        #print(r.status_code)
        citationStrList.append(r.text) # add the citation strings to the list

    scholex_df['PubCitationStr'] = citationStrList # add the citation string list to the Scholex df
    
    return scholex_df
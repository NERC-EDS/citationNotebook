# A function to retrieve citation information from Scholix API

# dataCite_df - the dataframe returned by function getNERCDataDOIs.py

def getScholixDatasetCitations(dataCite_df):
    import requests
    import numpy as np
    import pandas as pd
    import time
    
    scholexInfo = [] # create an empty list in which all the Scholex info will be placed
    
    dataDOIs = list(dataCite_df['datasetDOI_attribute'])
    dataPublisher = list(dataCite_df['publisher'])
    dataTitle = list(dataCite_df['title'])
    dataAuthors = list(dataCite_df['datasetAuthors_processed'])
    
    scholix_url = 'http://api.scholexplorer.openaire.eu/v2/Links?'

    # loop through info from the DataCite dataframe
    for doi, publisher, title, authors in zip(dataDOIs, dataPublisher, dataTitle, dataAuthors):
        headers = {'sourcePid': doi}
        r = requests.get(scholix_url, headers)
        print(headers)
        print('Status: ',  r.status_code)
               
        # scholex API holds no further info if no citations, therefore need a catcher to skip to the next record here
        if r.json()['totalLinks'] == 0:
            continue
        else:
            numPages = np.arange(0,r.json()['totalPages']) # create an array from 0 to the total number of pages of results to loop through

            for page in numPages:
                scholix_url_pages = scholix_url + 'page=' + str(page)
                r = requests.get(scholix_url_pages, headers)
                
                # if 'result' in r.json():
                try:
                    pageRecords = range(len(r.json()['result']))

                    # loop through records again to collect info this time - this needs to be a seperate block in order to add the completed citation count 
                    for citationNum in pageRecords:
                        
                        if "10.15468" in r.json()['result'][citationNum]['target']['Identifier'][0]['ID']: # skip the gbif records
                            print('Skip GBif')
                            continue
                        else:
                            for IDinfo in r.json()['result'][citationNum]['target']['Identifier']: # for each ID type for this publication e.g. DOI, pubmed etc
                                pubDOI = None

                                if IDinfo['IDScheme'] == 'doi':
                                    pubDOI =  IDinfo['ID']
                                    break
                                if IDinfo['IDScheme'] == 'handle':
                                    pubDOI =  IDinfo['ID']
                                    break
                                elif IDinfo['IDScheme'] == 'pmid':
                                    pubDOI =  IDinfo['ID']
                                elif IDinfo['IDScheme'] == 'pmc':
                                    pubDOI =  IDinfo['ID']
                                else:
                                    print('Unknown or new ID type:', IDinfo)
                                    pubDOI = str(IDinfo) # it must be someother ID scheme

#                             # there can be multiple ID schemes so we only want DOI of the publication:
#                             for IDinfo in r.json()['result'][citationNum]['target']['Identifier']: # for each ID type for this publication e.g. DOI, pubmed etc
#                                 if IDinfo['IDScheme'] == 'doi': # if its DOI, collect it and then skip to next part of code
#                                     pubDOI =  IDinfo['ID']
#                                     break
#                                 elif IDinfo['IDScheme'] == 'pmid':
#                                     pubDOI =  IDinfo['ID']
#                                 elif IDinfo['IDScheme'] == 'pmc':
#                                     pubDOI =  IDinfo['ID']
                                    
#                                 else: # if there's no DOI then collect all the ID (to be looked at manually later)
#                                     pubDOI =  r.json()['result'][citationNum]['target']['Identifier']

                            #only get certain relation types
                            if r.json()['result'][citationNum]['RelationshipType']['Name'] == "IsReferencedBy" or r.json()['result'][citationNum]['RelationshipType']['Name'] == 'IsRelatedTo':   
                                scholexInfo.append([
                                             r.json()['result'][citationNum]['RelationshipType']['Name'],
                                             r.json()['result'][citationNum]['target']['Title'],
                                             r.json()['result'][citationNum]['target']['PublicationDate'],
                                             r.json()['result'][citationNum]['target']['Creator'],
                                             pubDOI, 
                                             doi, publisher, title, authors]) # info from dataCite_df
                            else:
                                continue

                except:
                    # Handle the case when 'result' key is absent
                    print("No results found:", headers)
                
                
                
                
                    
    # put the collected info into a dataframe                
    column_names = ["relationshipType", "pubTitle", "pubDate", "pubAuthors", "pubID", "datasetDOI", "datasetPublisher", "datasetTitle", "datasetAuthors"]
    scholex_df = pd.DataFrame(scholexInfo, columns = column_names) 
    print('Done!')
    return scholex_df
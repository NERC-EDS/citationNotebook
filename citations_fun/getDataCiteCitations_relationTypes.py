# A function to collect all the datasets published by NERC on DataCite
#relation_type_id - a list of 'relation-type-id' types to be looped through, in the form 'is-referenced-by' - https://support.datacite.org/docs/connecting-to-works#summary-of-all-relationtypes

import requests
import numpy as np
import pandas as pd
import time
    
def getDataCiteCitations_relationTypes(relation_type_id_list):

    
    dataCite_info_relationTypes = []  # create an empty list in which all the DataCite info will be placed
    
    for relation_type_id in relation_type_id_list:
        dataCite_info = []

        # send a request to get initial info from DataCite
        headers = {
        'prefix': '10.5285',
        'page[cursor]': '1',
        'page[size]': '1000',
        'relation-type-id': relation_type_id
        }
        r = requests.get('https://api.datacite.org/events', headers,  timeout=30)
        
        print(relation_type_id)

        # determine the total number of pages and dataset records
        totalPages = r.json()['meta']['total-pages']
        totalRecords = r.json()['meta']['total']
        print("Total records:", totalRecords)
        print("Total pages:", totalPages)

        if totalRecords == 0:
            print(f"No records for {relation_type_id}, skipping")
            continue

        # create array from 1 to total number of pages to loop through
        pages = np.arange(1,totalPages+1)
        # set next page url
        if totalPages > 1:
            next_url = r.json()['links']['next']
        else:
            pass            

        #loop through pages
        for p in pages:

            MAX_PAGES = 1000
            if p > MAX_PAGES:
                raise RuntimeError("Pagination exceeded safety limit")
            
            if p == 1:
                url = 'https://api.datacite.org/events?page[cursor]=1'
            else:
                url = next_url

            # make the API request and print the status code in case of an error
            headers = {'prefix': '10.5285',
                       'page[size]': '1000',
                      'relation-type-id': relation_type_id
                      }
            r = requests.get(url,headers, timeout=30)
            print('Status: ', r.status_code)

            # determine status code, 
            if r.status_code == 200:
                pass
            elif r.status_code == 503: # if 503 error the server is overloaded, wait a bit then try again
                print('Waiting 2 mins for server to recover...?')
                time.sleep(120)
                r = requests.get(url, headers, timeout=30)
                print('Second attempt: ', r.status_code)
                if r.status_code == 503:
                    print("Server not recovered, try again later")
                    break
                else:
                    pass
            else:
                print("Something else has gone wrong while trying to contact the server!")
                break

            print('Page: ', p)

            # determine number of dataset records on this page
            numRecords = range(len(r.json()['data']))

            # loop through records on this page - this could be a separate function to call
            for recordNumber in numRecords:
                # add info to dataCiteInfo list
                dataCite_info.append([
                             # r.json()['data'][recordNumber]['id'],
                             r.json()['data'][recordNumber]['attributes']['subj-id'],
                             r.json()['data'][recordNumber]['attributes']['obj-id'],
                             r.json()['data'][recordNumber]['attributes']['source-id'],       
                             r.json()['data'][recordNumber]['attributes']['relation-type-id'], 
                             # r.json()['data'][recordNumber]['attributes']['occurred-at']
                             # r.json()['links']['self']
                             ])
            
            # print(dataCite_info)

            time.sleep(0.5) # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
            if p % 10 == 0: # if p is a multiple of 10 wait for a bit longer
                time.sleep(20)

            # for handling last page error - the code works by determining the endpoint of the next page and calling that, but needs an error catcher for the last page
            try:
                # determine url of next page
                next_url = r.json()['links']['next']
                print(next_url)
            except:
                print("Final page")
                break
            else:
                continue
            
        #append the retrieved list from the info with each relation tpye 
        dataCite_info_relationTypes.append(dataCite_info)

    # flatten and put the collected information into a pandas dataframe    
    flat_list = [item for sublist in dataCite_info_relationTypes for item in sublist]
    column_names = ["subj-id", "obj-id", "source_id", "relation_type"]
    dataCite_df = pd.DataFrame(flat_list, columns = column_names)


    doi_list = []
    for url in dataCite_df['subj-id']:
        doi = url.replace('https://doi.org/','')
        doi_list.append(doi)
    dataCite_df['data_doi'] = doi_list
    dataCite_df = dataCite_df.drop(['subj-id'], axis=1)
    
    dataCite_df = dataCite_df.rename(columns={"obj-id": "pub_doi"})

    # drop the rows where the data_doi column value does not start with "10.5285"
    dataCite_df = dataCite_df[dataCite_df['data_doi'].str.startswith('10.5285')]


    print('Done!')
    
    return dataCite_df
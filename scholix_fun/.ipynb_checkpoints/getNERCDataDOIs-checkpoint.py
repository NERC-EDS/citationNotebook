# A function to collect all the datasets published by NERC on DataCite

def getNERCDataDOIs():
    
    import requests
    import numpy as np
    import pandas as pd
    import time
    
    dataCiteInfo = []  # create an empty list in which all the DataCite info will be placed

    # send a request to get initial info from DataCite
    headers = {'client-id': 'bl.nerc', 'page': '1'} # defining this inside the request function doesn't work
    r = requests.get('https://api.datacite.org/dois', headers)

    # determine the total number of pages and dataset records
    totalPages = r.json()['meta']['totalPages']
    totalRecords = r.json()['meta']['total']
    print("Total records:", totalRecords)
    print("Total pages:", totalPages)

    # create array from 1 to total number of pages to loop through
    pages = np.arange(1,totalPages+1)
    # set next page url
    next_url = r.json()['links']['next']

    #loop through pages
    for p in pages:
        if p == 1:
            url = 'https://api.datacite.org/dois?page=1'
            # last page url number 130
            #url = 'https://api.datacite.org/dois?client-id=bl.nerc&page%5Bnumber%5D=130&page%5Bsize%5D=25&client-id=bl.nerc'
        else:
            url = next_url

        # make the API request and print the status code in case of an error
        headers = {'client-id': 'bl.nerc'}
        r = requests.get(url,headers)
        print('Status: ', r.status_code)
        
        # determine status code, 
        if r.status_code == 200:
            pass
        elif r.status_code == 503: # if 503 error the server is overloaded, wait a bit then try again
            print('Waiting 2 mins for server to recover...?')
            time.sleep(120)
            r = requests.get(url, headers)
            print('Second attempt: ', r.status_code)
            if r.status_code == 503:
                print("Server not recovered, try again later")
                break
            else:
                pass
        else:
            print("Something else has gone wrong!")
            break

        print('Page: ', r.json()['meta']['page'])

        # determine number of dataset records on this page
        numRecords = np.arange(0,(len(r.json()['data'])))

        # loop through records on this page - this could be a separate function to call
        for recordNumber in numRecords:
            # add info to dataCiteInfo list
            dataCiteInfo.append([r.json()['data'][recordNumber]['attributes']['publisher'],
                         r.json()['data'][recordNumber]['attributes']['doi'],
                         r.json()['data'][recordNumber]['attributes']['titles'],       
                         r.json()['data'][recordNumber]['attributes']['dates'], # remove this? Or change to just one date?
                         r.json()['data'][recordNumber]['attributes']['creators'],
                         r.json()['meta']['page'],
                         r.json()['links']['self']])

        time.sleep(1) # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
        if p % 10 == 0: # if p is a multiple of 10 wait for a bit longer
            time.sleep(30)

        # for handling last page error - the code works by determining the endpoint of the next page and calling that, but needs an error catcher for the last page
        try:
            # determine url of next page
            next_url = r.json()['links']['next']
        except:
            print("Final page")
            break
        else:
            continue
        
    # put the collected information into a pandas dataframe    
    column_names = ["publisher", "datasetDOI_attribute", "title_unprocessed", "dates", "creators", "page_number", "Page endpoint"]
    dataCite_df = pd.DataFrame(dataCiteInfo, columns = column_names)
    
    # process the title column
    title_lst = []
    for x in dataCite_df['title_unprocessed']:
        if len(x) == 0:
            title_lst.append('No title given')
        else:
            title_lst.append(x[0]['title'])

    #add processed title list to dataframe and delete unprocessed
    dataCite_df['title'] = title_lst
    dataCite_df = dataCite_df.drop(['title_unprocessed'], axis = 1)
    
    #process the authors column
    datasetAuthors_processed = []
    for authorList in dataCite_df['creators']:
        datasetAuthorList = []
        for individual in authorList:
            name = individual['name']
            datasetAuthorList.append(name)
        datasetAuthors_processed.append(datasetAuthorList)
    
    #add processed author list to dataframe and delete unprocessed
    dataCite_df['datasetAuthors_processed'] = datasetAuthors_processed
    dataCite_df = dataCite_df.drop(['creators'], axis = 1)
    
    print('Done!')
    
    return dataCite_df
# Check publication type 
def checkDOIpubType(publicationDOI):
    doi_url = 'https://doi.org/' + publicationDOI
    
    try:
        r = requests.get(doi_url, headers={"Accept": "application/json"}) # sometimes throws up unexpected errors
        print(r.status_code, publicationDOI)

        # sometimes the API call returns info in a format that is not JSON 
        pubType = r.json()['type'] # check if returned info is in json format and if there is publication type info
        print(pubType) 
        
        if 'subtype' in r.json() == True:
            pubSubType = r.json()['subtype']
            # print(pubType, ': ', publicationDOI)
        else:
            # print(pubType, ': ', publicationDOI)
            pubSubType = 'None'
            
    except Exception as e: # if unexpected error or returned info is not in json format put pubtype as unknown to be dealt with later
        # print('no json: ', publicationDOI)
        pubType = 'unknown'
        pubSubType = 'unknown'
          
    return pubType, pubSubType

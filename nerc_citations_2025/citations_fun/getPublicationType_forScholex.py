
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



# get publication type information
def getPublicationType(scholex_df):
    import requests
    import time
    import pandas as pd
    
    # takes > 60 mins
    # pass publication DOIs to DOI.org to determine type of publication using checkDOIpubType function defined above
    pubTypeList = []

    for count, doi in enumerate(scholex_df['pub_doi']):
        if '10.' in doi:
            pubType = checkDOIpubType(doi)
            pubTypeList.append(pubType)

        else:
            pubTypeList.append(["not a doi", "not a doi"])
            #its not a doi and can fill df cells with blanks for now - maybe find info on handles, pmids etc later


        # add code to catch retries limit exceeded - might need to be in function itself?
        # e.g. https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests

        time.sleep(0.1)
        if count + 1 % 500 == 0: # if count is a multiple of x wait for a bit
                time.sleep(60)

    print('Done!')

    scholex_df['publicationType'] = pubTypeList
    
    
    # split publicationType column into publicationType1 and publicationSubType columns
    scholex_df[['publicationType1','publicationSubType']] = pd.DataFrame(scholex_df['publicationType'].tolist(), index=scholex_df.index)
    
    
    # determine publication type for records where DOI.org API call failed - ~10 mins
    newPubTypeList = []

    # get the unknown rows from scholex_df pubtype column and the pubDOI
    for pubType, pubDOI in zip(scholex_df['publicationType1'],scholex_df['pub_doi']):

        if pubType == 'unknown':

            # need a catcher to make sure pubDOI is a single ID - in the cases where there was no DOI there is more than one ID recorded
            if len(pubDOI) < 100: # if the length is less than 100 (arbitrarily) then it will be a single DOI
                pass
            else: # if there is no DOI skip this record
                newPubTypeList.append(pubType) # leave it the same
                #newPubType = pubType 
                continue

            # determine if crossref or datacite supplies the DOI
            print('Pub DOI: ', pubDOI)
            r = requests.get(('https://doi.org/doiRA/' + pubDOI), headers={"Accept": "application/json"})
            
            try:
                DOIregistry = r.json()[0]['RA']
                print(DOIregistry)
            except (IndexError, KeyError) as e:
                print(f"Error accessing DOI registry: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")

            except (IndexError, KeyError) as e:
                print(f"Error accessing DOI registry: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")


            # query the crossref or datacite API
            if DOIregistry == 'DataCite':
                # ask the Datacite API what type of publication
                r = requests.get(('https://api.datacite.org/dois/' + pubDOI), headers = {'client-id': 'bl.nerc'})
                print(r.status_code)
                try:
                    newPubTypeList.append(r.json()['data']['attributes']['types']['citeproc']) # is citeproc the correct one to use?
                except:
                    newPubTypeList.append(pubType)

            elif DOIregistry == 'Crossref':
                r = requests.get(('https://api.crossref.org/works/'  + pubDOI), headers={"Accept": "application/json"})
                print(r.status_code)
                try:
                    newPubTypeList.append(r.json()['message']['type']) # could also add 'subtype':r.json()['message']['subtype']
                except:
                    newPubTypeList.append(pubType)
                    
            else:
                print('Unknown DOI registry')
                newPubTypeList.append(pubType)  # in the cases where the pubType is not unknown keep it the same

        else: 
            newPubTypeList.append(pubType) # in the cases where the pubType is not unknown keep it the same

    scholex_df['newPubTypeList'] = newPubTypeList
    print("Done")
    
    # tidy up scholex_df so we only have newPubTypeList
    scholex_df = scholex_df.drop(['publicationType', 'publicationType1', 'publicationSubType'], axis=1) # remove uneccessary columns
    scholex_df = scholex_df.rename(columns={"newPubTypeList": "PubType"})
    
    return scholex_df
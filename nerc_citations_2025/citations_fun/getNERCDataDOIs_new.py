import requests
import time
import json
import numpy as np
import pandas as pd
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pathlib import Path



def getNERCDataDOIs():
    """
    A function to collect all the datasets published by NERC on DataCite

    """

    
    # Helper functions for processing
    def extract_title(title_list):
        if isinstance(title_list, list) and title_list:
            return title_list[0].get("title", "No title given")
        return "No title given"
    
    def process_creators(creators):
        if isinstance(creators, list):
            return [individual.get('name', '') for individual in creators]
        return []
    

    # Setup a session with retries
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504], 
        raise_on_status=False  
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
  
    url = 'https://api.datacite.org/dois'
    params = {"client-id": "bl.nerc", "page": 1}
    headers = {"Accept": "application/json", 'client-id': 'bl.nerc'}
    dataCiteInfo = []  # create an empty list in which all the DataCite info will be placed


    # send a request to get initial info from DataCite
    try:
        r = session.get(url, headers=headers, params=params)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Initial API request failed: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on failure
    # parse the json 
    try:
        r_json = r.json()
        totalPages = r_json.get('meta', {}).get('totalPages', 0)
        # totalRecords = r_json.get('meta', {}).get('total', 0)
        next_url = r_json.get('links', {}).get('next')
    except ValueError as e:
        print(f"Error parsing JSON from initial request: {e}")
        return 
    
    # print(f"Total records: {totalRecords}, Total pages: {totalPages}")



    #loop through pages
    for p in range(1, totalPages + 1):
        if p == 1:
            data = r_json
            # url = 'https://api.datacite.org/dois?page=1'
            #url = 'https://api.datacite.org/dois?client-id=bl.nerc&page%5Bnumber%5D=130&page%5Bsize%5D=25&client-id=bl.nerc' # last page url number 130
        else:
            if not next_url:
                print("No next page URL provided. Ending loop.")
                break

            # make next request
            try:
                r = session.get(next_url, headers=headers)
                # wait for a bit, doing it too quickly may be overloading the server? often gives a 503 status error
                # time.sleep(1)
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Request for page {p} failed: {e}")
                continue

            try:
                data = r.json()
            except ValueError as e:
                print(f"Error decoding JSON on page {p}: {e}")
                continue
        
        records = data.get('data', [])

        # loop through records on this page 
        for record in records:
            attributes = record.get('attributes', {})
            publisher = attributes.get('publisher', '')
            doi = attributes.get('doi', '')
            title_unprocessed = attributes.get('titles', [])
            dates = attributes.get('dates', '')
            publicationYear = attributes.get('publicationYear', '')
            creators = attributes.get('creators', [])
            registered = attributes.get('registered', '') # is this correct? normally get it like this r.json()['data']['attributes']['registered'],

            page_number = data.get('meta', {}).get('page', p)
            self_link = data.get('links', {}).get('self', '')

            processed_title = extract_title(title_unprocessed)
            processed_creators = process_creators(creators)

            record_dict = {
                "publisher": publisher,
                "datasetDOI_attribute": doi,
                "title": processed_title,
                "dates": dates, 
                "publicationYear": publicationYear,
                "authors": processed_creators,
                "registered": registered,
                "page_number": page_number,
                "self_link": self_link
            }
            dataCiteInfo.append(record_dict)
        # Prepare the next_url for the upcoming page
        next_url = data.get('links', {}).get('next')
        if not next_url:
            print("Reached final page.")
            break

        # if p % 10 == 0: # if p is a multiple of 10 wait for a bit longer
        #     time.sleep(30)

    # # put the collected information into a pandas dataframe    
    # column_names = ["publisher", "datasetDOI_attribute", "title_unprocessed", "dates", "publication_yr", "creators", "page_number", "Page endpoint"]
    # dataCite_df = pd.DataFrame(dataCiteInfo, columns = column_names)




    # Write the collected data to a JSON file
    output_file = Path("results/nerc_datacite_dois.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)


    try:
        with open(output_file, 'w') as f:
            json.dump(dataCiteInfo, f, indent=4)
        print(f"Data written to {output_file}")
    except IOError as e:
        print(f"Error writing to file: {e}")
    
    print('Done!')
    
    return dataCiteInfo
def getCrossRefCitations_byDates(email, prefix, start_date, end_date, results_folder_path):
    import crossRef_fun
    # from crossRef_fun.eventData import eventData
    from crossRef_fun.eventData import eventData
    from math import ceil
    import json
    import pandas as pd
    import time
    import re
    import requests
    import datetime
    import os
    
    try:
        datetime.date.fromisoformat(start_date)
        datetime.date.fromisoformat(end_date)
    except Exception as e:
        print("start_date and/or end_date in wrong format. Should be yyyy-mm-dd")
        return

    # filename to save json event data to
    filename = results_folder_path + "event_data_" + prefix + "_" + start_date + "_" + end_date + ".json"

    # Set up the query
    ed = crossRef_fun.eventData(email = email, outputFile = filename)
    ed.buildQuery({'obj-id.prefix' : prefix, 'from-occurred-date' : start_date, 'until-occurred-date' : end_date}) 

    # run the query to determine number of events
    ed.runQuery(retry = 5) # scholix = False - can query scholix api as well - worth exploring

    # calculate how many pages will need to be iterated over
    num_pages = ceil(ed.events.count()/1000)

    # set up folder to result jsons into
    results_folder = results_folder_path + "NERC_EDS_events_from_" + start_date + "_up_to_" + end_date
    os.mkdir(results_folder) # not able to overwrite folder of the same name - delete folder and re-write?, or, add a folder with a new name each time?

    # find info from all the pages
    ed.getAllPages(num_pages, {'rows': 1000, 'obj-id.prefix' : prefix, 'from-occurred-date' : start_date, 'until-occurred-date' : end_date}, fileprefix = (results_folder + '/page')) # 
    
    
    
    
def getCrossRefCitations_byDOI(email, doi_list, results_folder_path_name):
    import crossRef_fun
    from crossRef_fun.eventData import eventData
    from math import ceil
    import json
    import requests
    import os

    # set up folder to result jsons into
    # results_folder = "NERC_EDS_events_from_doi_list_scholix"
    os.makedirs(results_folder_path_name, exist_ok=True)

    for count, doi in enumerate(doi_list):
        print(doi)

        fileDoi = doi.replace("/", "_")

        # Set up the query
        # filename to save json event data to
        filename = f"{results_folder_path_name}/event_data_{fileDoi}_{count}.json"
        ed = eventData(email=email, outputFile=filename)
        ed.buildQuery({'obj-id': doi})

        # run the query to determine number of events
        ed.runQuery(retry=5) # scholix = False - can query scholix api as well - worth exploring

        # calculate how many pages will need to be iterated over
        num_pages = ceil(ed.events.count()/1000)

        # find info from all the pages
        ed.getAllPages(num_pages, {'rows': 1000, 'obj-id': doi}, fileprefix=f"{results_folder_path_name}/{fileDoi}_page{count}") # fileDoi to give each result json a unique name, otherwise it writes over previous results 

    print('Done!')

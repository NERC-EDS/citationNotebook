NERC Data Centre Citations
V1.1 25/07/23

This code collects citation information from open API sources (Scholix, Crossref and Datacite) for datasets published by NERC data centres. 

The code combines the data from the three sources, removes duplicates and types of citations that we don't want to count, e.g. gbif or wikipedia mentions etc.
The data centre names (i.e. publishers) are made consistent.

The harvested data is not an exhaustive list of all the citations, and still contains some citations that are incorrect.

Usage
The code is written in Python in Jupyter notebooks. All the code has been compiled in one notebook nerc_dataset_citations_full_code.ipynb. Running the entire notebook takes several hours.
The folders CrossRef_fun, Scholix_fun and Datacite_fun contain functions relevant to collecting and processing data from each API. 
The Results folder contains the outputs of the code in csv and json format. The json is organised by each Data Centre as the top level keys.

The latest results are found in the file latest_results.json

Top level key:
data_Publisher	
Nested keys:
data_doi	data_Title	data_Authors	relation_type_id	publication_doi	publication_type	publication_title	publication_authors	citation_event_source	PubCitationStr


Authors:
Matthew Nichols (UKCEH)

Acknowledgments/references:
The functions to extract data from Crossref have been modified from the demo notebooks on the Crossref github (https://github.com/CrossRef/rest-api-doc)



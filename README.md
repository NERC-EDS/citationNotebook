# NERC Data Centre Citations

Collects citations of datasets published by the NERC Environmental Data Service (EDS) data centres from open APIs, merges and filters them, and publishes the results in `Results/v3/`, which the EDS citations API ingests.

This is not a complete list of every citation, and some of the citations it finds are wrong.

## How it runs

Each stage is a Jupyter notebook, run weekly by a GitHub Action with [papermill](https://papermill.readthedocs.io/). The Action commits the stage's output files back to `main`. The executed copy of each notebook is saved in `executed_notebooks/`, which is where to look for errors.

| Stage (Action) | Notebook | Schedule (Sunday, UTC) | Output |
|---|---|---|---|
| NERC dataset DOIs from DataCite | `nerc_dataset_DOIs.ipynb` | 00:00 | `Results/intermediate_data/nerc_datacite_dois.json` |
| DataCite citation events | `nerc_dataset_citations_dataCite.ipynb` | 02:00 | `Results/intermediate_data/latest_results_dataCite.csv` / `.pkl` |
| Scholexplorer (Scholix v3) | `nerc_dataset_citations_scholix.ipynb` | 04:00 | `Results/intermediate_data/latest_results_scholex.csv` / `.pkl` |
| Overton policy documents | `nerc_dataset_citations_overton.ipynb` | 12:00 | `Results/intermediate_data/latest_results_overton.csv` / `.pkl` |
| Merge, filter, citation strings | `nerc_dataset_citations_merge_results.ipynb` | 23:00 | `Results/v3/latest_results.csv` / `.json`, `Results/v3/filtered_out_df.csv` |

The three source stages each read `nerc_datacite_dois.json`, which also standardises the data centre names. The merge stage reads their `.pkl` files, so it uses whatever the source stages last committed. Each Action can also be run by hand from the Actions tab.

The merge stage:
- removes duplicate citations (same dataset DOI and publication DOI)
- filters out comments and replies on preprints, peer reviews, EGUsphere abstracts, GBIF downloads, and publications that pre-date the dataset (see `Results/v3/filtered_out_df.csv`)
- adds a formatted citation string for each publication
- keeps the `date_added` of citations already present in the previous results.

## Running locally

```
pip install -r requirements.txt
papermill nerc_dataset_citations_scholix.ipynb executed_notebooks/nerc_dataset_citations_scholix_executed.ipynb
```

Run from the repository root, since the notebooks use paths relative to it. The helper functions are in `citations_fun/`. A full run of all stages takes several hours. `inspect_results.ipynb` is for checking the results by hand.

## Output

`Results/v3/latest_results.csv` has one row per citation, with these columns:

`data_doi`, `data_publisher`, `data_title`, `data_publication_year`, `data_authors`, `relation_type_id`, `publication_doi`, `publication_title`, `publication_date`, `publication_authors`, `citation_event_source`, `pub_publisher`, `publication_type`, `publicationYear`, `PubCitationStr`, `data_doi_url`, `publication_doi_url`, `date_added`

`Results/v3/latest_results.json` holds the same records, grouped under the data centre (`data_publisher`) as the top-level key.

`Results/v1/` and `Results/v2/` hold earlier versions of the results. The pipeline no longer updates them.

## Authors

Matthew Nichols (UKCEH)

## Acknowledgements

The Crossref functions were adapted from the demo notebooks in the Crossref [rest-api-doc](https://github.com/CrossRef/rest-api-doc) repository.

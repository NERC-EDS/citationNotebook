import pandas as pd


def filterCitations(nerc_citations_df):
    """
    Remove citations we don't want to surface, returning (kept_df, filtered_out_df).

    Fixes vs the previous version:
      * The kept frame is now carried forward through every step. Previously the
        peer-review step recomputed `nerc_citations_df_filtered` from the ORIGINAL
        input, silently undoing the comment/reply title filter.
      * Years are coerced with pd.to_numeric(errors="coerce"); rows whose
        publication year can't be parsed (None / "Info not given" / "API request
        failed") now end up NaN and are KEPT, instead of being silently dropped
        from both the kept and filtered-out frames (a likely contributor to
        "missing citations", issue #11). A non-numeric value also no longer
        crashes .astype("float").
      * .str accessors use na=False so NaN titles/types/DOIs don't raise.
    """
    df = nerc_citations_df.copy()
    filtered_out_parts = []

    # 1. Comments / replies on pre-prints (by title prefix).
    title_filters = ("Comment on", "Reply on", "Reply to comment by", "final response")
    is_comment = df["pub_title"].str.startswith(title_filters, na=False)
    filtered_out_parts.append(df[is_comment])
    df = df[~is_comment]

    # 2. Peer-review publication type.
    is_peer_review = df["pub_type"].str.startswith("peer-review", na=False)
    filtered_out_parts.append(df[is_peer_review])
    df = df[~is_peer_review]

    # 3. Unwanted publication DOIs:
    #    "egusphere" -> always a conference abstract; "10.15468" -> GBIF dataset downloads.
    #    (10\.15468 is escaped so the dot matches a literal dot, not any character.)
    pub_doi_pattern = "|".join(("egusphere", r"10\.15468"))
    is_excluded_doi = df["pub_doi"].str.contains(pub_doi_pattern, na=False, regex=True)
    filtered_out_parts.append(df[is_excluded_doi])
    df = df[~is_excluded_doi]

    # 4. The publication must not pre-date the data it cites.
    #    Coerce both years to numeric; unparseable -> NaN. NaN comparisons are
    #    False, so rows with an unknown year are kept (not dropped).
    pub_year = pd.to_numeric(df["publicationYear"], errors="coerce")
    data_year = pd.to_numeric(df["data_publication_year"], errors="coerce")
    predates_data = pub_year < data_year
    filtered_out_parts.append(df[predates_data])
    df = df[~predates_data]

    filtered_out_df = (pd.concat(filtered_out_parts, ignore_index=True)
                       if filtered_out_parts else df.iloc[0:0].copy())

    return (df, filtered_out_df)
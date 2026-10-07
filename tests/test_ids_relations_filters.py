import pytest

from citations import filters, ids, relations


@pytest.mark.parametrize("value, scheme, expected", [
    ("10.1016/J.SCITOTENV.2012.05.023", None, ("10.1016/j.scitotenv.2012.05.023", "doi")),
    ("https://doi.org/10.1111/1365-2656.12728", None, ("10.1111/1365-2656.12728", "doi")),
    ("http://dx.doi.org/10.5194/HESS-23-4527-2019", None, ("10.5194/hess-23-4527-2019", "doi")),
    ("https://pubs.acs.org/doi/10.1021/acs.est.9b02292", None, ("10.1021/acs.est.9b02292", "doi")),
    ("https://www.Rand.org/pubs/research_reports/RR2695.html/", None, ("https://rand.org/pubs/research_reports/RR2695.html", "url")),
    ("https://example.org/report?utm_source=x&id=7#top", None, ("https://example.org/report?id=7", "url")),
    ("123456", "pmid", ("pmid:123456", "pmid")),
    ("PMC12345", "pmc", ("pmc:PMC12345", "pmc")),
    ("http://hdl.handle.net/10013/epic.1", "handle", ("hdl:10013/epic.1", "handle")),
    ("not a doi", None, None),
    ("Info not given", None, None),
    (None, None, None),
])
def test_normalise_id(value, scheme, expected):
    assert ids.normalise_id(value, scheme=scheme) == expected


def test_case_and_url_variants_merge():
    # The four v3 duplicates that differed only by URL case now get one id.
    a = ids.normalise_id("http://naturvardsverket.diva-portal.org/smash/get/diva2:1717304/fulltext01.pdf")
    b = ids.normalise_id("http://naturvardsverket.diva-portal.org/smash/get/diva2:1717304/FULLTEXT01.pdf")
    assert a[1] == b[1] == "url"
    assert ids.normalise_id("https://doi.org/10.1234/ABC") == ids.normalise_id("10.1234/abc")


def test_self_reference_is_not_an_identifier():
    assert ids.normalise_id("https://doi.org/10.5285/ABC", exclude="10.5285/abc") is None


def test_link_id_is_stable():
    assert ids.link_id("10.5285/a", "10.1/b") == ids.link_id("10.5285/a", "10.1/b")
    assert ids.link_id("10.5285/a", "10.1/b") != ids.link_id("10.5285/a", "10.1/c")


@pytest.mark.parametrize("relation, side, expected", [
    ("references", "object", "IsReferencedBy"),        # Crossref: article references dataset
    ("cites", "object", "IsCitedBy"),
    ("is-referenced-by", "subject", "IsReferencedBy"),  # DataCite metadata: dataset is referenced by article
    ("IsReferencedBy", "subject", "IsReferencedBy"),
    ("hasamongtopnsimilardocuments", "object", "HasAmongTopNSimilarDocuments"),
    ("isnewversionof", "object", "IsPreviousVersionOf"),
    ("issourceof", "object", "IsDerivedFrom"),           # outgoing: the dataset derives from the source
])
def test_dataset_side(relation, side, expected):
    assert relations.dataset_side(relation, side) == expected


@pytest.mark.parametrize("relation, klass", [
    ("IsCitedBy", "citation"),
    ("IsReferencedBy", "citation"),
    ("IsSupplementTo", "supplement"),
    ("IsSupplementedBy", "supplement"),
    ("IsDocumentedBy", "documentation"),
    ("IsPartOf", "version-or-part"),
    ("HasAmongTopNSimilarDocuments", "similarity"),
    ("References", None),       # the dataset cites the other work: outgoing
    ("Cites", None),
    ("IsDerivedFrom", None),
])
def test_relation_class(relation, klass):
    assert relations.relation_class(relation) == klass


def test_kebab():
    assert relations.to_kebab("IsReferencedBy") == "is-referenced-by"


def reason(**kw):
    base = dict(data_doi="10.5285/d", citing_id="10.1/w", relation_class="citation",
                work={"title": "A study", "issued": "2020-01-01"}, dataset_year=2020, tolerance_years=2)
    base.update(kw)
    return filters.exclusion_reason(**base)


def test_included_by_default():
    assert reason() is None


def test_predates_tolerance_is_two_years():
    assert reason(work={"issued": "2019"}) is None                 # one year before: kept
    assert reason(work={"issued": "2018-12-31"}) == "predates-data"
    assert reason(work={"issued": None}) is None                   # unknown year: kept, never silently dropped


def test_predates_only_applies_to_uses_of_the_data():
    assert reason(work={"issued": "2001"}, relation_class="similarity") is None
    assert reason(work={"issued": "2001"}, relation_class="version-or-part") is None


@pytest.mark.parametrize("kw, expected", [
    (dict(citing_id="10.5285/d"), "self-link"),
    (dict(work={"title": "Comment on essd-2021-65", "issued": "2021"}), "comment"),
    (dict(work={"title": "Review", "work_type": "peer-review", "issued": "2021"}), "peer-review"),
    (dict(citing_id="10.5194/egusphere-egu21-123"), "conference-abstract"),
    (dict(citing_id="10.15468/dl.abc"), "gbif-download"),
])
def test_exclusion_reasons(kw, expected):
    assert reason(**kw) == expected

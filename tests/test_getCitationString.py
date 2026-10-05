"""Offline tests for citations_fun.getCitationString (no network)."""
import pandas as pd
import pytest

from citations_fun import getCitationString as gcs

ERRORS_SEEN_IN_RESULTS = [
    "Unknown style frontiers-of-biogeography",
    "DOI exists but metadata could not be retrieved - contact info@doi.org for help with this",
    "DOI not found",
    "not a doi",
    "error occurred",
]


@pytest.mark.parametrize("value, expected", [
    ("10.1016/j.scitotenv.2012.05.023", "10.1016/j.scitotenv.2012.05.023"),
    ("https://doi.org/10.1111/1365-2656.12728", "10.1111/1365-2656.12728"),
    ("doi:10.5194/cp-2017-18", "10.5194/cp-2017-18"),
    ("https://pubs.acs.org/doi/10.1021/acs.est.9b02292", "10.1021/acs.est.9b02292"),
    ("https://iopscience.iop.org/article/10.1088/2515-7620/ab48da", "10.1088/2515-7620/ab48da"),
    ("10.1016/10.1111/jbi.13501", "10.1111/jbi.13501"),          # doubled prefix
    ("https://doi.org/10.5285%2Fabc-123", "10.5285/abc-123"),     # URL-encoded
    ("https://peerj.com/manuscripts/29426", None),
    ("https://example.org/page?ref=10.5285/abc-123", None),       # DOI only in query
    ("not a doi", None),
    (None, None),
    (float("nan"), None),
])
def test_normalise_doi(value, expected):
    assert gcs.normalise_doi(value) == expected


def test_normalise_doi_ignores_the_cited_dataset():
    assert gcs.normalise_doi("https://catalogue.example/doc/10.5285/abc", data_doi="10.5285/ABC") is None


STYLE_NOT_FOUND = ('{"code":"style-not-found","message":"Style [frontiers-of-biogeography] does not exist",'
                   '"doi":"10.1111\\/1365-2656.12728"}')
APA = ("Griffiths, H. M., Ashton, L. A., Walker, A. E., Hasan, F., Evans, T. A., Eggleton, P., & Parr, C. L. "
       "(2017). Ants are the major agents of resource removal from tropical rainforests. Journal of Animal "
       "Ecology, 87(1), 293\u2013300. Portico. https://doi.org/10.1111/1365-2656.12728")


@pytest.mark.parametrize("text", ERRORS_SEEN_IN_RESULTS + ["", None, "<html><body>503</body></html>", STYLE_NOT_FOUND])
def test_error_values_are_not_citations(text):
    assert not gcs.is_real_citation(text)


def test_real_citation_with_not_found_in_title_is_kept():
    text = "Smith J. (2020). Species not found in surveys of upland soils. Ecology 12, 1-9."
    assert gcs.is_real_citation(text)


@pytest.mark.parametrize("authors, expected", [
    ("[['N.A.', 'Beresford'], ['C.L.', 'Barnett'], ['J.', 'Vives i Batlle'], ['E.D.', 'Potter']]",
     "Beresford N.A., Barnett C.L., Vives i Batlle J., et al."),
    ("['Bentley, L.', 'Reinsch, S.']", "Bentley, L., Reinsch, S."),
    ("['Joint Nature Conservation Committee']", "Joint Nature Conservation Committee"),
    ("[['Government of Northwest Territories']]", "Government of Northwest Territories"),
    ("Info not given", ""),
    ("not a doi", ""),
])
def test_authors(authors, expected):
    assert gcs._authors(authors) == expected


def test_fallback_for_url_identified_work():
    row = {"pub_title": "Scoping the use of predictive models", "pub_authors": "['Joint Nature Conservation Committee']",
           "publicationYear": "2019", "pub_publisher": "Joint Nature Conservation Committee"}
    # An organisation that is both author and publisher is named once.
    assert gcs.fallback_citation(row) == (
        "Joint Nature Conservation Committee (2019). Scoping the use of predictive models."
    )


def test_fallback_with_doi_and_date_only():
    row = {"pub_title": "Ants are the major agents.", "pub_authors": "[['Hannah M.', 'Griffiths']]",
           "publicationYear": None, "pub_date": "9/8/2017", "pub_publisher": "Wiley"}
    assert gcs.fallback_citation(row, "10.1111/1365-2656.12728") == (
        "Griffiths H.M. (2017). Ants are the major agents. Wiley. https://doi.org/10.1111/1365-2656.12728"
    )


def test_fallback_without_title_is_empty():
    row = {"pub_title": "not a doi", "pub_authors": "not a doi", "pub_publisher": "not a doi"}
    assert gcs.fallback_citation(row) == ""


class FakeResponse:
    def __init__(self, status, text):
        self.status_code, self.text, self.encoding = status, text, None


class FakeSession:
    """Answers like the formatter: a fixed body per DOI, else the error seen since Feb 2026."""
    def __init__(self, good):
        self.good, self.calls = good, []

    def get(self, url, headers=None, timeout=None):
        doi = url.split("doi.org/", 1)[1]
        self.calls.append(doi)
        if doi in self.good:
            return FakeResponse(200, self.good[doi])
        return FakeResponse(200, "Unknown style frontiers-of-biogeography")


def frame(rows):
    cols = ["data_doi", "pub_doi", "pub_title", "pub_authors", "publicationYear", "pub_date", "pub_publisher"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows])


GOOD = "Griffiths, H. M., et al. (2017). Ants are the major agents of resource removal. J. Anim. Ecol."


def test_end_to_end(monkeypatch):
    session = FakeSession({"10.1111/1365-2656.12728": GOOD})
    monkeypatch.setattr(gcs, "_session", lambda: session)
    df = frame([
        ("10.5285/d1", "10.1111/1365-2656.12728", "Ants", "[]", "2017", "", "Wiley"),
        ("10.5285/d2", "10.1111/1365-2656.12728", "Ants", "[]", "2017", "", "Wiley"),    # same pub: one lookup
        ("10.5285/d1", "10.1016/j.x.2020.1", "A failing DOI", "['Smith, J.']", "2020", "", "Elsevier"),
        ("10.5285/d1", "https://example.org/report", "A policy report", "['Some Agency']", "2021", "", "Some Agency"),
        ("10.5285/d1", "https://peerj.com/m/1", "not a doi", "not a doi", None, "Info not given", "not a doi"),
        ("10.5285/d3", "10.5194/reused", "Reused", "[]", "2019", "", "Copernicus"),
    ])
    previous = pd.DataFrame({"publication_doi": ["10.5194/reused", "10.1016/j.x.2020.1"],
                             "PubCitationStr": ["Prior, A. (2019). A citation kept from last week. Copernicus.",
                                                "Unknown style frontiers-of-biogeography"]})
    out = gcs.get_citation_str(df, previous_results=previous, min_success_rate=None, pause=0)
    s = out["pub_citation_str"].tolist()
    assert s[0] == GOOD and s[1] == GOOD
    assert s[2] == "Smith, J. (2020). A failing DOI. Elsevier. https://doi.org/10.1016/j.x.2020.1"
    assert s[3] == "Some Agency (2021). A policy report."
    assert s[4] == ""
    assert s[5] == "Prior, A. (2019). A citation kept from last week. Copernicus."
    assert not any(e in x for x in s for e in ERRORS_SEEN_IN_RESULTS if e)
    assert sorted(session.calls) == ["10.1016/j.x.2020.1", "10.1111/1365-2656.12728"]


def test_raises_when_formatter_is_broken(monkeypatch):
    monkeypatch.setattr(gcs, "_session", lambda: FakeSession({}))
    df = frame([("10.5285/d", f"10.1000/{i}", "T", "[]", "2020", "", "P") for i in range(25)])
    with pytest.raises(RuntimeError, match="0 of 25"):
        gcs.get_citation_str(df, pause=0)


def test_real_doi_org_apa_response_is_accepted():
    # Verbatim response from doi.org content negotiation, 2026-10-05.
    assert gcs.is_real_citation(APA)


def test_requests_apa_by_default(monkeypatch):
    seen = {}

    class Session:
        def get(self, url, headers=None, timeout=None):
            seen["accept"] = headers["Accept"]
            return FakeResponse(200, APA)

    monkeypatch.setattr(gcs, "_session", lambda: Session())
    out = gcs.get_citation_str(frame([("10.5285/d", "10.1111/1365-2656.12728", "Ants", "[]", "2017", "", "Wiley")]),
                               min_success_rate=None, pause=0)
    assert seen["accept"] == "text/x-bibliography; style=apa; locale=en-GB"
    assert out["pub_citation_str"].iloc[0] == APA


def test_style_not_found_falls_back_even_with_http_200(monkeypatch):
    class Session:
        def get(self, url, headers=None, timeout=None):
            return FakeResponse(200, STYLE_NOT_FOUND)

    monkeypatch.setattr(gcs, "_session", lambda: Session())
    out = gcs.get_citation_str(frame([("10.5285/d", "10.1111/x", "Ants", "['Griffiths, H.']", "2017", "", "Wiley")]),
                               min_success_rate=None, pause=0)
    assert out["pub_citation_str"].iloc[0] == "Griffiths, H. (2017). Ants. Wiley. https://doi.org/10.1111/x"

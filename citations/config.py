"""Settings, constants and the data-centre mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__

CODE_VERSION = __version__
NERC_PREFIX = "10.5285/"

# Sources the pipeline harvests. A required source must have a successful,
# recent harvest or publishing is refused; an optional one only warns.
REQUIRED_SOURCES = ("datacite", "scholexplorer")
OPTIONAL_SOURCES = ("overton", "crossref")
ALL_SOURCES = REQUIRED_SOURCES + OPTIONAL_SOURCES

CENTRE_NAMES = {
    "BODC": "British Oceanographic Data Centre (BODC)",
    "CEDA": "Centre for Environmental Data Analysis (CEDA)",
    "EIDC": "Environmental Information Data Centre (EIDC)",
    "NGDC": "National Geoscience Data Centre (NGDC)",
    "PDC": "Polar Data Centre (PDC)",
}
UNKNOWN_CENTRE_NAME = "Unknown data centre"


def data_centre(publisher: str | None) -> str | None:
    """EDS data-centre code for a DataCite publisher name, or None.

    The same keyword rules as the v3 pipeline (getNERCDataDOIs.process_publisher),
    returning a short code instead of the long name.
    """
    if not isinstance(publisher, str) or not publisher.strip():
        return None
    p = publisher.lower()
    if "polar" in p:
        return "PDC"
    if "atmospheric" in p or "badc" in p or "earth" in p:
        return "CEDA"
    if "oceanographic" in p:
        return "BODC"
    if "geological" in p or "geoscience" in p:
        return "NGDC"
    if "environmental information" in p:
        return "EIDC"
    if "environmental data" in p:
        return "CEDA"
    return None


@dataclass
class Settings:
    db_path: Path = Path("data/citations.sqlite")
    results_dir: Path = Path("Results")
    client_id: str = "bl.nerc"
    mailto: str | None = field(default_factory=lambda: os.environ.get("CITATIONS_MAILTO") or None)
    overton_api_key: str | None = field(default_factory=lambda: os.environ.get("OVERTON_API_KEY") or None)
    workers: int = 4
    # Publishing guards
    max_source_age_days: float = 8
    max_row_drop: float = 0.20          # a harvest losing more than this share of rows is rejected
    max_error_rate: float = 0.02        # share of failed per-DOI requests that makes a harvest partial
    reconcile_threshold: float = 0.05   # share of DataCite-cited datasets allowed to be incomplete
    # Classification
    predates_tolerance_years: int = 2   # exclude a work published this many years or more before the dataset
    # Caching / resume
    resume_window_days: float = 6       # an unfinished harvest younger than this is resumed, not restarted
    works_refresh_days: float = 90      # re-fetch citing-work metadata after this long
    min_citation_success_rate: float = 0.5
    write_v3: bool = True

    @property
    def v4_dir(self) -> Path:
        return self.results_dir / "v4"

    @property
    def v3_dir(self) -> Path:
        return self.results_dir / "v3"

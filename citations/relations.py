"""Relation vocabulary: every source's relation, seen from the dataset's side, and its class.

All relations are stored in the DataCite vocabulary (CamelCase) as they apply to
the *dataset*: "IsCitedBy" means the other work cites the dataset. A source that
states the link from the citing work's side ("article references dataset") is
inverted. Relations where the dataset is the one doing the citing or deriving
("dataset References article", "dataset IsDerivedFrom X") are *outgoing*: they
are not links to the dataset and are dropped at harvest.
"""

from __future__ import annotations

import re

# DataCite relationType pairs (https://datacite-metadata-schema.readthedocs.io/en/4.5/appendices/appendix-1/relationType/)
_PAIRS = [
    ("IsCitedBy", "Cites"),
    ("IsSupplementTo", "IsSupplementedBy"),
    ("IsContinuedBy", "Continues"),
    ("IsDescribedBy", "Describes"),
    ("HasMetadata", "IsMetadataFor"),
    ("HasVersion", "IsVersionOf"),
    ("IsNewVersionOf", "IsPreviousVersionOf"),
    ("IsPartOf", "HasPart"),
    ("IsReferencedBy", "References"),
    ("IsDocumentedBy", "Documents"),
    ("IsCompiledBy", "Compiles"),
    ("IsVariantFormOf", "IsOriginalFormOf"),
    ("IsIdenticalTo", "IsIdenticalTo"),
    ("IsReviewedBy", "Reviews"),
    ("IsDerivedFrom", "IsSourceOf"),
    ("IsRequiredBy", "Requires"),
    ("IsObsoletedBy", "Obsoletes"),
    ("IsCollectedBy", "Collects"),
    ("IsTranslationOf", "HasTranslation"),
    ("IsPublishedIn", "IsPublishedIn"),
]
SIMILARITY = "HasAmongTopNSimilarDocuments"

INVERSE: dict[str, str] = {}
for a, b in _PAIRS:
    INVERSE[a], INVERSE[b] = b, a
INVERSE[SIMILARITY] = SIMILARITY

VOCABULARY = {name.lower(): name for name in INVERSE}

# Dataset-side relation -> class. Anything not listed is outgoing.
CLASS_OF = {
    "IsCitedBy": "citation",
    "IsReferencedBy": "citation",
    # Supplements are direction-agnostic: data centres write "dataset IsSupplementTo
    # article", while DataCite counts "X is-supplement-to dataset" as a citation.
    "IsSupplementTo": "supplement",
    "IsSupplementedBy": "supplement",
    "IsDocumentedBy": "documentation",
    "IsDescribedBy": "documentation",
    "IsReviewedBy": "documentation",
    "IsRequiredBy": "other",
    "IsSourceOf": "other",          # the other work is derived from the dataset
    "Compiles": "other",            # the dataset is used to compile the other work
    "IsPartOf": "version-or-part",
    "HasPart": "version-or-part",
    "IsNewVersionOf": "version-or-part",
    "IsPreviousVersionOf": "version-or-part",
    "HasVersion": "version-or-part",
    "IsVersionOf": "version-or-part",
    "Continues": "version-or-part",
    "IsContinuedBy": "version-or-part",
    "IsVariantFormOf": "version-or-part",
    "IsOriginalFormOf": "version-or-part",
    "Obsoletes": "version-or-part",
    "IsObsoletedBy": "version-or-part",
    "IsIdenticalTo": "version-or-part",
    SIMILARITY: "similarity",
}

CLASSES = ("citation", "supplement", "documentation", "other", "dataset-link", "version-or-part", "similarity")
# When two sources disagree about one pair, the most specific evidence wins.
PRIORITY = {"citation": 6, "supplement": 5, "documentation": 4, "other": 3, "version-or-part": 2, "similarity": 1}
COUNTED_CLASSES = {"citation", "supplement"}
# Classes for which "the work pre-dates the dataset" means the link is doubtful.
USE_CLASSES = {"citation", "supplement", "documentation", "other"}


def canonical(relation: str | None) -> str | None:
    """'is-referenced-by', 'isreferencedby', 'IsReferencedBy' -> 'IsReferencedBy'; unknown -> None."""
    if not relation:
        return None
    key = re.sub(r"[^a-z]", "", str(relation).lower())
    return VOCABULARY.get(key)


def dataset_side(relation: str | None, dataset_is: str) -> str | None:
    """The relation from the dataset's side.

    `relation` is stated subject -> object. If the dataset is the subject it is
    already dataset-side; if the dataset is the object it is inverted.
    """
    name = canonical(relation)
    if name is None:
        return None
    if dataset_is == "subject":
        return name
    if dataset_is == "object":
        return INVERSE.get(name)
    raise ValueError(f"dataset_is must be 'subject' or 'object', not {dataset_is!r}")


def relation_class(dataset_relation: str | None) -> str | None:
    """Class of a dataset-side relation, or None when the relation is outgoing."""
    if dataset_relation is None:
        return None
    return CLASS_OF.get(dataset_relation)


def is_incoming(dataset_relation: str | None) -> bool:
    return relation_class(dataset_relation) is not None


def to_kebab(name: str) -> str:
    """'IsReferencedBy' -> 'is-referenced-by' (the DataCite events spelling)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()

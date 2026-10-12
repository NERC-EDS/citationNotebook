"""Link sources. Each module exposes ``SOURCE`` and ``harvest(ctx, run_id) -> {"details": {...}}``."""

from . import crossref, datacite, overton, scholexplorer

MODULES = {
    datacite.SOURCE: datacite,
    scholexplorer.SOURCE: scholexplorer,
    overton.SOURCE: overton,
    crossref.SOURCE: crossref,
}

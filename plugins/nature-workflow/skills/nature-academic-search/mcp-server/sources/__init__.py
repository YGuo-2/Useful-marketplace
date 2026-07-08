"""Data source modules for academic search."""

from .crossref import CrossRefSource
from .pubmed import PubMedSource
from .arxiv import ArxivSource
from .scopus import ScopusSource
from .sciencedirect import ScienceDirectSource
from .openalex import OpenAlexSource
from .unpaywall import UnpaywallSource

__all__ = [
    "CrossRefSource",
    "PubMedSource",
    "ArxivSource",
    "ScopusSource",
    "ScienceDirectSource",
    "OpenAlexSource",
    "UnpaywallSource",
]

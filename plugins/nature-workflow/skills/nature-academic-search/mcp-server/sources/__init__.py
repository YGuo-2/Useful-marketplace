"""Data source modules for academic search."""

from .crossref import CrossRefSource
from .pubmed import PubMedSource
from .arxiv import ArxivSource
from .scopus import ScopusSource
from .sciencedirect import ScienceDirectSource
from .openalex import OpenAlexSource
from .unpaywall import UnpaywallSource
from .europepmc import EuropePmcSource
from .semanticscholar import SemanticScholarSource

__all__ = [
    "CrossRefSource",
    "PubMedSource",
    "ArxivSource",
    "ScopusSource",
    "ScienceDirectSource",
    "OpenAlexSource",
    "UnpaywallSource",
    "EuropePmcSource",
    "SemanticScholarSource",
]

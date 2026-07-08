"""Europe PMC data source for academic search.

Free, no API key required. Europe PMC indexes life-science literature (PubMed +
PMC full text, Agricola, patents) and biomedical preprints (bioRxiv/medRxiv),
so it is a strong T1 complement to PubMed with abstracts and citation counts.
"""

import re

import requests

from utils.config import get_config
from utils.errors import DataSourceError

EUROPEPMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest"

_DOI_RE = re.compile(r"^10\.\d+/.+")
_DOI_URL_RE = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)


def _clean_doi(doi: str) -> str:
    """Strip a full DOI URL down to the bare ``10.<registrant>/<suffix>`` form."""
    return _DOI_URL_RE.sub("", (doi or "").strip())


def _truncate_authors(names: list[str], limit: int = 5) -> list[str]:
    """Trim a flat author-name list to ``limit`` names, appending ``et al.``."""
    clean = [n.strip() for n in names if n and n.strip()]
    if limit and len(clean) > limit:
        return clean[:limit] + ["et al."]
    return clean


class EuropePmcSource:
    """Europe PMC REST API wrapper with the unified result format."""

    SOURCE_NAME = "europepmc"

    def __init__(self):
        config = get_config()
        self._timeout = config.europepmc_timeout
        self._headers = {
            "User-Agent": "ClaudeCode-MCP-EuropePMC/1.0 (mailto:user@example.com)",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, rows: int = 5, filter_type: str | None = None) -> dict:
        """Search Europe PMC.

        Args:
            query: Free-text query (title/abstract/author/etc.).
            rows: Number of results (max 100).
            filter_type: Unused; kept for a uniform source signature.

        Returns:
            {"total": int, "results": [unified_result, ...]}
        """
        if not query or not query.strip():
            raise DataSourceError(self.SOURCE_NAME, "Empty search query")

        params = {
            "query": query.strip(),
            "format": "json",
            "resultType": "core",  # includes abstract + authorList + journalInfo
            "pageSize": min(max(rows, 1), 100),
        }
        data = self._request("/search", params=params)
        items = (data.get("resultList") or {}).get("result", [])
        total = data.get("hitCount", 0)
        results = [self._normalize_search_item(item) for item in items]
        return {"total": total, "results": results}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, path: str, params: dict | None = None) -> dict:
        """Issue GET to the Europe PMC API and return the parsed JSON body."""
        url = f"{EUROPEPMC_API}{path}"
        try:
            resp = requests.get(
                url, params=params, headers=self._headers, timeout=self._timeout
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            raise DataSourceError(
                self.SOURCE_NAME, f"HTTP {status} from {url}", original_error=exc
            ) from exc
        except requests.RequestException as exc:
            raise DataSourceError(
                self.SOURCE_NAME,
                f"Network error calling {url}: {exc}",
                original_error=exc,
            ) from exc
        return resp.json()

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _authors(item: dict) -> list[str]:
        """Author names from authorList, falling back to the flat authorString."""
        author_list = (item.get("authorList") or {}).get("author") or []
        names = [a.get("fullName", "") for a in author_list]
        names = [n for n in names if n]
        if not names and item.get("authorString"):
            names = [n.strip(" .") for n in item["authorString"].split(",")]
        return _truncate_authors(names, limit=5)

    @staticmethod
    def _year(item: dict) -> int | None:
        raw = item.get("pubYear")
        try:
            return int(raw) if raw else None
        except (TypeError, ValueError):
            return None

    def _normalize_search_item(self, item: dict) -> dict:
        """Map a Europe PMC result to the unified search result format."""
        journal = ((item.get("journalInfo") or {}).get("journal") or {}).get("title", "")
        return {
            "title": item.get("title") or "",
            "authors": self._authors(item),
            "year": self._year(item),
            "doi": _clean_doi(item.get("doi") or "") or None,
            "journal": journal or "",
            "source": self.SOURCE_NAME,
            "citation_count": item.get("citedByCount", 0),
        }

"""Semantic Scholar (Academic Graph) data source for academic search.

Cross-disciplinary corpus with a strong citation graph and field-of-study
filters. An API key is optional: anonymous access is ~1 req/s (HTTP 429 when
exceeded); an ``x-api-key`` raises the limit. Requested fields must be listed
explicitly or the API returns only ``paperId``.
"""

import re

import requests

from utils.config import get_config
from utils.errors import DataSourceError

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
_SEARCH_FIELDS = "title,authors,year,externalIds,abstract,citationCount,venue"

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


class SemanticScholarSource:
    """Semantic Scholar Graph API wrapper with the unified result format."""

    SOURCE_NAME = "semanticscholar"

    def __init__(self):
        config = get_config()
        self._api_key = config.semanticscholar_api_key or ""
        self._timeout = config.semanticscholar_timeout
        self._headers = {
            "User-Agent": "ClaudeCode-MCP-SemanticScholar/1.0",
        }
        if self._api_key:
            self._headers["x-api-key"] = self._api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, rows: int = 5, filter_type: str | None = None) -> dict:
        """Search Semantic Scholar papers.

        Args:
            query: Free-text query.
            rows: Number of results (max 100).
            filter_type: Unused; kept for a uniform source signature.

        Returns:
            {"total": int, "results": [unified_result, ...]}
        """
        if not query or not query.strip():
            raise DataSourceError(self.SOURCE_NAME, "Empty search query")

        params = {
            "query": query.strip(),
            "limit": min(max(rows, 1), 100),
            "fields": _SEARCH_FIELDS,
        }
        # ponytail: no 429 backoff — this source is opt-in and _search_all
        # degrades gracefully on failure; set an api_key to lift the rate limit.
        data = self._request("/paper/search", params=params)
        items = [item for item in data.get("data", []) if item]
        total = data.get("total", 0)
        results = [self._normalize_search_item(item) for item in items]
        return {"total": total, "results": results}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, path: str, params: dict | None = None) -> dict:
        """Issue GET to the Semantic Scholar API and return the parsed JSON body."""
        url = f"{SEMANTIC_SCHOLAR_API}{path}"
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

    def _normalize_search_item(self, item: dict) -> dict:
        """Map a Semantic Scholar paper to the unified search result format."""
        names = [(a or {}).get("name", "") for a in item.get("authors") or []]
        doi = (item.get("externalIds") or {}).get("DOI")
        return {
            "title": item.get("title") or "",
            "authors": _truncate_authors(names, limit=5),
            "year": item.get("year"),
            "doi": _clean_doi(doi or "") or None,
            "journal": item.get("venue") or "",
            "source": self.SOURCE_NAME,
            "citation_count": item.get("citationCount", 0) or 0,
        }

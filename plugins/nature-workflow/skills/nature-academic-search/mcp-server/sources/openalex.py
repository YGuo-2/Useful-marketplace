"""OpenAlex data source for academic search.

Free, no API key required. A ``mailto`` address opts into OpenAlex's faster
"polite pool". OpenAlex has broad cross-disciplinary coverage (works, citations,
venues, institutions, concepts) and is a practical open substitute for Web of
Science / Scopus discovery.
"""

import re
from urllib.parse import quote

import requests

from utils.config import get_config
from utils.errors import DataSourceError

OPENALEX_API = "https://api.openalex.org"

_DOI_RE = re.compile(r"^10\.\d+/.+")
_DOI_URL_RE = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)


def _clean_doi(doi: str) -> str:
    """Strip a full DOI URL down to the bare ``10.<registrant>/<suffix>`` form."""
    return _DOI_URL_RE.sub("", (doi or "").strip())


def _validate_doi(doi: str) -> str:
    """Reject anything that is not a canonical DOI so it cannot rewrite the path."""
    doi = _clean_doi(doi)
    if not _DOI_RE.match(doi):
        raise ValueError(f"Invalid DOI: {doi!r}")
    return doi


def _rebuild_abstract(inverted_index: dict | None) -> str:
    """Rebuild a plain-text abstract from OpenAlex's inverted-index form.

    OpenAlex returns ``abstract_inverted_index`` as ``{word: [positions...]}``;
    reorder the words by position to recover readable text.
    """
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positions)


class OpenAlexSource:
    """OpenAlex API wrapper with the unified result format."""

    SOURCE_NAME = "openalex"

    def __init__(self):
        config = get_config()
        self._mailto = config.openalex_mailto or ""
        self._timeout = config.openalex_timeout
        self._headers = {
            "User-Agent": (
                "ClaudeCode-MCP-OpenAlex/1.0 "
                f"(mailto:{self._mailto or 'user@example.com'})"
            ),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, rows: int = 5, filter_type: str | None = None) -> dict:
        """Search OpenAlex works.

        Args:
            query: Free-text query (title/abstract/fulltext).
            rows: Number of results (max 50).
            filter_type: Optional work type filter, e.g. "article".

        Returns:
            {"total": int, "results": [unified_result, ...]}
        """
        if not query or not query.strip():
            raise DataSourceError(self.SOURCE_NAME, "Empty search query")

        params: dict = {"search": query.strip(), "per-page": min(max(rows, 1), 50)}
        if filter_type:
            params["filter"] = f"type:{filter_type}"
        if self._mailto:
            params["mailto"] = self._mailto

        data = self._request("/works", params=params)
        items = data.get("results", [])
        total = data.get("meta", {}).get("count", 0)
        results = [self._normalize_search_item(item) for item in items]
        return {"total": total, "results": results}

    def get_by_doi(self, doi: str) -> dict:
        """Get detailed metadata for a single work by DOI."""
        clean = _validate_doi(doi)
        params: dict = {}
        if self._mailto:
            params["mailto"] = self._mailto
        data = self._request(f"/works/doi:{quote(clean, safe='/')}", params=params)
        return self._normalize_detail_item(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, path: str, params: dict | None = None) -> dict:
        """Issue GET to the OpenAlex API and return the parsed JSON body."""
        url = f"{OPENALEX_API}{path}"
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
    def _extract_authors(authorships: list[dict], limit: int = 0) -> list[str]:
        """Convert OpenAlex authorships to a ``["Given Family", ...]`` list."""
        subset = authorships[:limit] if limit else authorships
        names = [
            (a.get("author") or {}).get("display_name", "").strip() for a in subset
        ]
        names = [n for n in names if n]
        if limit and len(authorships) > limit:
            names.append("et al.")
        return names

    @staticmethod
    def _journal(item: dict) -> str:
        """Best-effort host venue name from primary_location."""
        loc = item.get("primary_location") or {}
        src = loc.get("source") or {}
        return src.get("display_name", "") or ""

    def _normalize_search_item(self, item: dict) -> dict:
        """Map an OpenAlex work to the unified search result format."""
        return {
            "title": item.get("display_name") or item.get("title") or "",
            "authors": self._extract_authors(item.get("authorships", []), limit=5),
            "year": item.get("publication_year"),
            "doi": _clean_doi(item.get("doi") or "") or None,
            "journal": self._journal(item),
            "source": self.SOURCE_NAME,
            "citation_count": item.get("cited_by_count", 0),
        }

    def _normalize_detail_item(self, item: dict) -> dict:
        """Map an OpenAlex work to the unified detail result format."""
        base = self._normalize_search_item(item)
        oa = item.get("open_access") or {}
        base.update({
            "authors": self._extract_authors(item.get("authorships", [])),
            "abstract": _rebuild_abstract(item.get("abstract_inverted_index")),
            "type": item.get("type"),
            "openalex_id": item.get("id"),
            "referenced_works_count": item.get("referenced_works_count", 0),
            "is_oa": oa.get("is_oa", False),
            "oa_url": oa.get("oa_url"),
            "url": item.get("doi") or item.get("id"),
        })
        return base

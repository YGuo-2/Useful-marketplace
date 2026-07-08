"""Unpaywall data source: legal open-access full-text lookup by DOI.

Given a DOI, Unpaywall returns the best *legal* open-access location (publisher
OA, repository green OA, etc.) — never paywalled or pirated sources. Requires an
email (free; identifies the caller per Unpaywall's usage policy).
"""

import re
from urllib.parse import quote

import requests

from utils.config import get_config
from utils.errors import DataSourceError

UNPAYWALL_API = "https://api.unpaywall.org/v2"

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


class UnpaywallSource:
    """Unpaywall wrapper returning the best legal OA full-text location."""

    SOURCE_NAME = "unpaywall"

    def __init__(self):
        config = get_config()
        self._email = config.unpaywall_email or ""
        self._timeout = config.unpaywall_timeout

    def get_oa(self, doi: str) -> dict:
        """Look up the best open-access location for a DOI.

        Returns a unified dict with ``is_oa``, ``oa_status``, ``pdf_url``,
        ``landing_url``, ``license``, and ``version``. A DOI unknown to
        Unpaywall returns ``is_oa: False`` with a note rather than raising.
        """
        if not self._email:
            raise DataSourceError(
                self.SOURCE_NAME,
                "Unpaywall requires an email; set [unpaywall] email in "
                "config.toml or the UNPAYWALL_EMAIL env var",
            )
        try:
            clean = _validate_doi(doi)
        except ValueError as exc:
            raise DataSourceError(self.SOURCE_NAME, str(exc)) from exc

        url = f"{UNPAYWALL_API}/{quote(clean, safe='/')}"
        try:
            resp = requests.get(url, params={"email": self._email}, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DataSourceError(
                self.SOURCE_NAME,
                f"Network error calling {url}: {exc}",
                original_error=exc,
            ) from exc

        if resp.status_code == 404:
            return {
                "doi": clean,
                "is_oa": False,
                "source": self.SOURCE_NAME,
                "note": "DOI not found in Unpaywall",
            }
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise DataSourceError(
                self.SOURCE_NAME,
                f"HTTP {resp.status_code} from {url}",
                original_error=exc,
            ) from exc

        return self._normalize(resp.json())

    def _normalize(self, data: dict) -> dict:
        """Map an Unpaywall response to the unified OA result format."""
        best = data.get("best_oa_location") or {}
        raw_doi = data.get("doi") or ""
        return {
            "doi": _clean_doi(raw_doi) or None,
            "is_oa": data.get("is_oa", False),
            "oa_status": data.get("oa_status"),
            "title": data.get("title", ""),
            "journal": data.get("journal_name", ""),
            "year": data.get("year"),
            "pdf_url": best.get("url_for_pdf"),
            "landing_url": best.get("url"),
            "license": best.get("license"),
            "version": best.get("version"),
            "host_type": best.get("host_type"),
            "oa_location_count": len(data.get("oa_locations") or []),
            "source": self.SOURCE_NAME,
        }

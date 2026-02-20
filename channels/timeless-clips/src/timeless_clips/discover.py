"""Internet Archive content discovery."""

from __future__ import annotations

import contextlib
import logging
import time

import httpx

from timeless_clips.catalog import Catalog
from timeless_clips.models import ArchiveItem

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://archive.org/advancedsearch.php"
_METADATA_URL = "https://archive.org/metadata"

# Pre-built search queries by category
QUERIES = {
    "ads": "collection:prelinger AND subject:advertising",
    "educational": "collection:prelinger AND subject:educational",
    "film": "collection:feature_films AND year:[1895 TO 1928]",
    "speech": ("collection:audio AND subject:speeches AND mediatype:audio"),
    "nasa": "collection:nasa AND mediatype:movies",
    "newsreel": ("collection:newsandpublicaffairs AND mediatype:movies"),
}

# Allowed licenses for monetized content
_ALLOWED_LICENSES = {
    "publicdomain",
    "",
    "Public Domain",
    "public domain",
    "http://creativecommons.org/publicdomain/zero/1.0/",
    "http://creativecommons.org/licenses/by/4.0/",
    "http://creativecommons.org/licenses/by/3.0/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
    "https://creativecommons.org/licenses/by/4.0/",
}


class ContentDiscoverer:
    """Search Internet Archive for public domain content."""

    def __init__(self, config: dict, client: httpx.Client | None = None):
        self._config = config.get("archive", {})
        self._rate_limit = self._config.get("rate_limit_seconds", 1.0)
        self._client = client or httpx.Client(timeout=30)
        self._last_request = 0.0

    def _throttle(self):
        """Rate limit requests."""
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request = time.monotonic()

    def search(self, query: str, max_results: int = 50) -> list[ArchiveItem]:
        """Search IA Advanced Search and return items."""
        self._throttle()
        params = {
            "q": query,
            "fl[]": [
                "identifier",
                "title",
                "description",
                "year",
                "licenseurl",
                "collection",
            ],
            "sort[]": "downloads desc",
            "rows": str(max_results),
            "output": "json",
        }
        resp = self._client.get(_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
        items = []
        for doc in docs:
            collection = doc.get("collection", "")
            if isinstance(collection, list):
                collection = collection[0] if collection else ""
            item = ArchiveItem(
                identifier=doc.get("identifier", ""),
                title=doc.get("title", "Unknown"),
                description=doc.get("description", ""),
                year=(doc.get("year") if doc.get("year") else None),
                collection=collection,
                license_info=doc.get("licenseurl", ""),
                source_url=(f"https://archive.org/details/{doc.get('identifier', '')}"),
            )
            items.append(item)
        return items

    def search_category(self, category: str, max_results: int = 50) -> list[ArchiveItem]:
        """Search using a pre-built category query."""
        query = QUERIES.get(category)
        if not query:
            raise ValueError(f"Unknown category: {category}. Available: {list(QUERIES)}")
        items = self.search(query, max_results)
        for item in items:
            item.category = category
        return items

    def filter_usable(self, items: list[ArchiveItem]) -> list[ArchiveItem]:
        """Filter to items with allowed licenses only."""
        return [item for item in items if item.license_info in _ALLOWED_LICENSES]

    def get_metadata(self, identifier: str) -> dict:
        """Fetch full metadata for an item."""
        self._throttle()
        resp = self._client.get(f"{_METADATA_URL}/{identifier}")
        resp.raise_for_status()
        return resp.json()

    def enrich_item(self, item: ArchiveItem, metadata: dict) -> ArchiveItem:
        """Enrich an item with download URLs and metadata."""
        files = metadata.get("files", [])
        preferred = self._config.get("preferred_formats", ["mp4", "ogv", "avi"])
        base = f"https://archive.org/download/{item.identifier}"
        download_urls = []
        for fmt in preferred:
            for f in files:
                name = f.get("name", "")
                if name.lower().endswith(f".{fmt}"):
                    download_urls.append(f"{base}/{name}")
        item.download_urls = download_urls
        # Try to get duration from metadata
        md = metadata.get("metadata", {})
        if not item.year and md.get("year"):
            with contextlib.suppress(ValueError, TypeError):
                item.year = int(md["year"])
        if not item.description and md.get("description"):
            desc = md["description"]
            item.description = desc if isinstance(desc, str) else str(desc)
        return item

    def discover_and_catalog(
        self,
        catalog: Catalog,
        category: str,
        max_results: int = 50,
    ) -> int:
        """Search, filter, enrich, and save to catalog.

        Returns count of newly saved items.
        """
        items = self.search_category(category, max_results)
        usable = self.filter_usable(items)
        count = 0
        for item in usable:
            if catalog.get_item(item.identifier):
                continue  # already in catalog
            try:
                metadata = self.get_metadata(item.identifier)
                item = self.enrich_item(item, metadata)
                catalog.save_item(item, metadata=metadata)
                count += 1
            except httpx.HTTPError:
                logger.warning(
                    "Failed to fetch metadata for %s",
                    item.identifier,
                )
        return count

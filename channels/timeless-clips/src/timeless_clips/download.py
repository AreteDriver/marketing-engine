"""Media file downloader with caching."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

from timeless_clips.catalog import Catalog
from timeless_clips.models import ArchiveItem

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Download and cache media files from Internet Archive."""

    def __init__(self, config: dict, client: httpx.Client | None = None):
        self._config = config.get("archive", {})
        self._cache_dir = Path(self._config.get("cache_dir", "cache"))
        self._rate_limit = self._config.get("rate_limit_seconds", 1.0)
        self._preferred = self._config.get("preferred_formats", ["mp4", "ogv", "avi"])
        self._client = client or httpx.Client(timeout=120, follow_redirects=True)
        self._last_request = 0.0

    def _throttle(self):
        """Rate limit requests."""
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request = time.monotonic()

    def get_cache_path(self, item: ArchiveItem) -> Path:
        """Return the local cache directory for an item."""
        return self._cache_dir / item.collection / item.identifier

    def download(
        self,
        item: ArchiveItem,
        catalog: Catalog | None = None,
    ) -> Path:
        """Download the best available file for an item.

        Returns local path to the downloaded file.

        Raises ValueError if no download URLs available.
        """
        if not item.download_urls:
            raise ValueError(f"No download URLs for {item.identifier}")

        url = self._select_best_url(item.download_urls)
        cache_path = self.get_cache_path(item)
        cache_path.mkdir(parents=True, exist_ok=True)

        filename = url.rsplit("/", 1)[-1]
        local_path = cache_path / filename

        if local_path.exists():
            logger.info("Using cached file: %s", local_path)
            return local_path

        self._throttle()
        logger.info("Downloading %s -> %s", url, local_path)

        with self._client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        if catalog:
            catalog.set_local_path(item.identifier, str(local_path))

        return local_path

    def _select_best_url(self, urls: list[str]) -> str:
        """Select the best URL based on preferred format order."""
        for fmt in self._preferred:
            for url in urls:
                if url.lower().endswith(f".{fmt}"):
                    return url
        # Fallback to first URL
        return urls[0]

    def is_cached(self, item: ArchiveItem) -> bool:
        """Check if media file is already cached."""
        cache_path = self.get_cache_path(item)
        if not cache_path.exists():
            return False
        return any(cache_path.iterdir())

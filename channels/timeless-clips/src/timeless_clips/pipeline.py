"""Timeless Clips pipeline orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

from timeless_clips.captions import CaptionGenerator
from timeless_clips.catalog import Catalog
from timeless_clips.compose import ShortComposer
from timeless_clips.config import get_config_path, load_config
from timeless_clips.discover import ContentDiscoverer
from timeless_clips.download import MediaDownloader
from timeless_clips.extract_moment import MomentExtractor
from timeless_clips.models import ArchiveItem
from timeless_clips.narration import NarrationGenerator

logger = logging.getLogger(__name__)


class TimelessClipsPipeline:
    """Full pipeline: discover -> download -> extract -> narrate -> caption -> compose."""

    def __init__(
        self,
        config: dict | None = None,
        catalog: Catalog | None = None,
        discoverer: ContentDiscoverer | None = None,
        downloader: MediaDownloader | None = None,
        extractor: MomentExtractor | None = None,
        narrator: NarrationGenerator | None = None,
        captioner: CaptionGenerator | None = None,
        composer: ShortComposer | None = None,
    ) -> None:
        self._config = config or load_config(get_config_path())
        db_path = self._config.get("catalog", {}).get("db_path", "catalog.db")
        self._catalog = catalog or Catalog(db_path)
        self._discoverer = discoverer or ContentDiscoverer(self._config)
        self._downloader = downloader or MediaDownloader(self._config)
        self._extractor = extractor or MomentExtractor(self._config)
        self._narrator = narrator or NarrationGenerator(self._config)
        self._captioner = captioner or CaptionGenerator(self._config)
        self._composer = composer or ShortComposer(self._config)

    def discover(self, category: str, max_results: int = 50) -> int:
        """Run discovery for a category. Returns count of new items."""
        return self._discoverer.discover_and_catalog(self._catalog, category, max_results)

    def process_batch(self, category: str | None = None, batch_size: int = 5) -> list[Path]:
        """Process a batch of unprocessed items into Shorts."""
        items = self._catalog.get_unprocessed(category=category, limit=batch_size)
        results: list[Path] = []
        for item in items:
            try:
                path = self.process_single(item)
                results.append(path)
            except Exception:
                logger.exception("Failed to process %s", item.identifier)
        return results

    def process_single(self, item: ArchiveItem) -> Path:
        """Process a single item through the full pipeline."""
        output_dir = Path(self._config.get("output", {}).get("output_dir", "output"))
        work_dir = output_dir / item.identifier
        work_dir.mkdir(parents=True, exist_ok=True)

        # Download source media
        source_path = self._downloader.download(item, self._catalog)

        # Extract compelling moment
        script = self._extractor.extract(item)

        # Generate narration
        narration_path = self._narrator.generate(script, work_dir)

        # Generate captions
        caption_path = self._captioner.generate(narration_path, work_dir, item.identifier)

        # Compose final Short
        output_path = work_dir / f"{item.identifier}_short.mp4"
        self._composer.compose(script, source_path, narration_path, caption_path, output_path)

        # Mark as processed
        self._catalog.mark_processed(item.identifier, str(output_path))
        logger.info("Completed Short: %s", output_path)
        return output_path

    def get_stats(self) -> dict:
        """Return catalog statistics."""
        return self._catalog.get_stats()

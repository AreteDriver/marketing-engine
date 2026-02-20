"""Tests for timeless_clips.pipeline — TimelessClipsPipeline orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from timeless_clips.models import ArchiveItem, ShortScript, TextOverlay
from timeless_clips.pipeline import TimelessClipsPipeline


def _make_item(identifier: str = "test-item") -> ArchiveItem:
    """Create a minimal ArchiveItem for testing."""
    return ArchiveItem(
        identifier=identifier,
        title=f"Test Item {identifier}",
        description="A test archive item.",
        year=1955,
        collection="prelinger",
        source_url=f"https://archive.org/details/{identifier}",
        download_urls=[f"https://archive.org/download/{identifier}/video.mp4"],
        duration=120.0,
        category="educational",
        tags=["test"],
    )


def _make_script(item_id: str = "test-item") -> ShortScript:
    """Create a ShortScript for testing."""
    return ShortScript(
        item_id=item_id,
        hook="You won't believe this",
        start_time=10.0,
        end_time=40.0,
        narration="Narration text.",
        text_overlays=[TextOverlay(time=2.0, text="1955")],
        closing="Follow for more.",
        category="educational",
        mood="nostalgic",
        tags=["test"],
    )


@pytest.fixture()
def mock_deps(tmp_path: Path) -> dict[str, MagicMock]:
    """Create all mock dependencies for the pipeline."""
    config = {
        "catalog": {"db_path": str(tmp_path / "catalog.db")},
        "output": {"output_dir": str(tmp_path / "output")},
    }
    catalog = MagicMock()
    discoverer = MagicMock()
    downloader = MagicMock()
    extractor = MagicMock()
    narrator = MagicMock()
    captioner = MagicMock()
    composer = MagicMock()

    return {
        "config": config,
        "catalog": catalog,
        "discoverer": discoverer,
        "downloader": downloader,
        "extractor": extractor,
        "narrator": narrator,
        "captioner": captioner,
        "composer": composer,
    }


def _make_pipeline(deps: dict) -> TimelessClipsPipeline:
    """Create a pipeline with all dependencies injected."""
    return TimelessClipsPipeline(
        config=deps["config"],
        catalog=deps["catalog"],
        discoverer=deps["discoverer"],
        downloader=deps["downloader"],
        extractor=deps["extractor"],
        narrator=deps["narrator"],
        captioner=deps["captioner"],
        composer=deps["composer"],
    )


class TestPipelineInit:
    """Tests for TimelessClipsPipeline initialization."""

    def test_init_with_injected_deps(self, mock_deps: dict) -> None:
        pipeline = _make_pipeline(mock_deps)
        assert pipeline._config == mock_deps["config"]
        assert pipeline._catalog is mock_deps["catalog"]
        assert pipeline._discoverer is mock_deps["discoverer"]
        assert pipeline._downloader is mock_deps["downloader"]
        assert pipeline._extractor is mock_deps["extractor"]
        assert pipeline._narrator is mock_deps["narrator"]
        assert pipeline._captioner is mock_deps["captioner"]
        assert pipeline._composer is mock_deps["composer"]

    @patch("timeless_clips.pipeline.ShortComposer")
    @patch("timeless_clips.pipeline.CaptionGenerator")
    @patch("timeless_clips.pipeline.NarrationGenerator")
    @patch("timeless_clips.pipeline.MomentExtractor")
    @patch("timeless_clips.pipeline.MediaDownloader")
    @patch("timeless_clips.pipeline.ContentDiscoverer")
    @patch("timeless_clips.pipeline.Catalog")
    @patch("timeless_clips.pipeline.load_config")
    @patch("timeless_clips.pipeline.get_config_path")
    def test_init_without_config_loads_default(
        self,
        mock_get_path: MagicMock,
        mock_load: MagicMock,
        mock_catalog: MagicMock,
        mock_discoverer: MagicMock,
        mock_downloader: MagicMock,
        mock_extractor: MagicMock,
        mock_narrator: MagicMock,
        mock_captioner: MagicMock,
        mock_composer: MagicMock,
    ) -> None:
        mock_get_path.return_value = Path("configs/config.yaml")
        mock_load.return_value = {"catalog": {"db_path": "catalog.db"}}
        TimelessClipsPipeline()
        mock_get_path.assert_called_once()
        mock_load.assert_called_once_with(Path("configs/config.yaml"))

    @patch("timeless_clips.pipeline.ShortComposer")
    @patch("timeless_clips.pipeline.CaptionGenerator")
    @patch("timeless_clips.pipeline.NarrationGenerator")
    @patch("timeless_clips.pipeline.MomentExtractor")
    @patch("timeless_clips.pipeline.MediaDownloader")
    @patch("timeless_clips.pipeline.ContentDiscoverer")
    @patch("timeless_clips.pipeline.Catalog")
    def test_init_with_config_skips_load(
        self,
        mock_catalog: MagicMock,
        mock_discoverer: MagicMock,
        mock_downloader: MagicMock,
        mock_extractor: MagicMock,
        mock_narrator: MagicMock,
        mock_captioner: MagicMock,
        mock_composer: MagicMock,
    ) -> None:
        cfg = {"catalog": {"db_path": "test.db"}}
        pipeline = TimelessClipsPipeline(config=cfg)
        assert pipeline._config is cfg


class TestDiscover:
    """Tests for TimelessClipsPipeline.discover."""

    def test_discover_delegates_to_discoverer(self, mock_deps: dict) -> None:
        mock_deps["discoverer"].discover_and_catalog.return_value = 7
        pipeline = _make_pipeline(mock_deps)
        count = pipeline.discover("educational", max_results=25)
        assert count == 7
        mock_deps["discoverer"].discover_and_catalog.assert_called_once_with(
            mock_deps["catalog"], "educational", 25
        )

    def test_discover_default_max_results(self, mock_deps: dict) -> None:
        mock_deps["discoverer"].discover_and_catalog.return_value = 0
        pipeline = _make_pipeline(mock_deps)
        pipeline.discover("ads")
        mock_deps["discoverer"].discover_and_catalog.assert_called_once_with(
            mock_deps["catalog"], "ads", 50
        )


class TestProcessSingle:
    """Tests for TimelessClipsPipeline.process_single."""

    def test_process_single_calls_all_stages(self, mock_deps: dict, tmp_path: Path) -> None:
        item = _make_item("stage-test")
        script = _make_script("stage-test")
        source_path = tmp_path / "source.mp4"
        narration_path = tmp_path / "narration.wav"
        caption_path = tmp_path / "captions.srt"
        mock_deps["downloader"].download.return_value = source_path
        mock_deps["extractor"].extract.return_value = script
        mock_deps["narrator"].generate.return_value = narration_path
        mock_deps["captioner"].generate.return_value = caption_path

        pipeline = _make_pipeline(mock_deps)
        pipeline.process_single(item)

        # Verify call order: download -> extract -> narrate -> caption -> compose -> mark
        mock_deps["downloader"].download.assert_called_once_with(item, mock_deps["catalog"])
        mock_deps["extractor"].extract.assert_called_once_with(item)
        mock_deps["narrator"].generate.assert_called_once()
        mock_deps["captioner"].generate.assert_called_once()
        mock_deps["composer"].compose.assert_called_once()
        mock_deps["catalog"].mark_processed.assert_called_once()

    def test_process_single_returns_output_path(self, mock_deps: dict, tmp_path: Path) -> None:
        item = _make_item("path-test")
        mock_deps["downloader"].download.return_value = tmp_path / "source.mp4"
        mock_deps["extractor"].extract.return_value = _make_script("path-test")
        mock_deps["narrator"].generate.return_value = tmp_path / "narration.wav"
        mock_deps["captioner"].generate.return_value = tmp_path / "captions.srt"

        pipeline = _make_pipeline(mock_deps)
        result = pipeline.process_single(item)

        expected_dir = Path(mock_deps["config"]["output"]["output_dir"]) / "path-test"
        expected = expected_dir / "path-test_short.mp4"
        assert result == expected

    def test_process_single_creates_work_dir(self, mock_deps: dict, tmp_path: Path) -> None:
        item = _make_item("mkdir-test")
        mock_deps["downloader"].download.return_value = tmp_path / "source.mp4"
        mock_deps["extractor"].extract.return_value = _make_script("mkdir-test")
        mock_deps["narrator"].generate.return_value = tmp_path / "narration.wav"
        mock_deps["captioner"].generate.return_value = tmp_path / "captions.srt"

        pipeline = _make_pipeline(mock_deps)
        pipeline.process_single(item)

        work_dir = Path(mock_deps["config"]["output"]["output_dir"]) / "mkdir-test"
        assert work_dir.exists()

    def test_process_single_marks_processed(self, mock_deps: dict, tmp_path: Path) -> None:
        item = _make_item("mark-test")
        mock_deps["downloader"].download.return_value = tmp_path / "source.mp4"
        mock_deps["extractor"].extract.return_value = _make_script("mark-test")
        mock_deps["narrator"].generate.return_value = tmp_path / "narration.wav"
        mock_deps["captioner"].generate.return_value = tmp_path / "captions.srt"

        pipeline = _make_pipeline(mock_deps)
        pipeline.process_single(item)

        mark_call = mock_deps["catalog"].mark_processed.call_args
        assert mark_call[0][0] == "mark-test"
        assert "mark-test_short.mp4" in mark_call[0][1]


class TestProcessBatch:
    """Tests for TimelessClipsPipeline.process_batch."""

    def test_process_batch_returns_paths(self, mock_deps: dict, tmp_path: Path) -> None:
        items = [_make_item("b1"), _make_item("b2")]
        mock_deps["catalog"].get_unprocessed.return_value = items
        mock_deps["downloader"].download.return_value = tmp_path / "source.mp4"
        mock_deps["extractor"].extract.side_effect = [_make_script("b1"), _make_script("b2")]
        mock_deps["narrator"].generate.return_value = tmp_path / "narration.wav"
        mock_deps["captioner"].generate.return_value = tmp_path / "captions.srt"

        pipeline = _make_pipeline(mock_deps)
        results = pipeline.process_batch(category="educational", batch_size=5)

        assert len(results) == 2
        mock_deps["catalog"].get_unprocessed.assert_called_once_with(
            category="educational", limit=5
        )

    def test_process_batch_no_category(self, mock_deps: dict) -> None:
        mock_deps["catalog"].get_unprocessed.return_value = []
        pipeline = _make_pipeline(mock_deps)
        results = pipeline.process_batch()
        assert results == []
        mock_deps["catalog"].get_unprocessed.assert_called_once_with(category=None, limit=5)

    def test_process_batch_handles_exception_gracefully(
        self, mock_deps: dict, tmp_path: Path
    ) -> None:
        items = [_make_item("ok"), _make_item("fail"), _make_item("ok2")]
        mock_deps["catalog"].get_unprocessed.return_value = items

        # First succeeds, second fails, third succeeds
        mock_deps["downloader"].download.side_effect = [
            tmp_path / "source.mp4",
            RuntimeError("download failed"),
            tmp_path / "source.mp4",
        ]
        mock_deps["extractor"].extract.side_effect = [_make_script("ok"), _make_script("ok2")]
        mock_deps["narrator"].generate.return_value = tmp_path / "narration.wav"
        mock_deps["captioner"].generate.return_value = tmp_path / "captions.srt"

        pipeline = _make_pipeline(mock_deps)
        results = pipeline.process_batch(batch_size=3)

        # Two successful, one failed
        assert len(results) == 2

    def test_process_batch_empty_catalog(self, mock_deps: dict) -> None:
        mock_deps["catalog"].get_unprocessed.return_value = []
        pipeline = _make_pipeline(mock_deps)
        results = pipeline.process_batch(category="film")
        assert results == []


class TestGetStats:
    """Tests for TimelessClipsPipeline.get_stats."""

    def test_get_stats_delegates_to_catalog(self, mock_deps: dict) -> None:
        expected = {
            "total": 10,
            "processed": 3,
            "unprocessed": 7,
            "by_category": {"ads": 5, "film": 5},
            "by_collection": {"prelinger": 10},
        }
        mock_deps["catalog"].get_stats.return_value = expected
        pipeline = _make_pipeline(mock_deps)
        stats = pipeline.get_stats()
        assert stats == expected
        mock_deps["catalog"].get_stats.assert_called_once()

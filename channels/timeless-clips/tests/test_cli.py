"""Tests for timeless_clips.cli — Typer CLI commands."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from timeless_clips import __version__
from timeless_clips.cli import app
from timeless_clips.models import ArchiveItem

runner = CliRunner()


def _make_item(identifier: str = "test-item") -> ArchiveItem:
    """Create a minimal ArchiveItem for CLI tests."""
    return ArchiveItem(
        identifier=identifier,
        title=f"Test {identifier}",
        collection="prelinger",
        source_url=f"https://archive.org/details/{identifier}",
        download_urls=[f"https://archive.org/download/{identifier}/video.mp4"],
        category="educational",
    )


class TestVersion:
    """Tests for the --version flag."""

    def test_version_long_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_value(self) -> None:
        assert __version__ == "0.1.0"


class TestMainModule:
    """Tests for __main__.py entry point."""

    def test_main_invokes_app(self) -> None:
        with pytest.raises(SystemExit):
            runpy.run_module("timeless_clips", run_name="__main__")


class TestDiscoverCommand:
    """Tests for the 'discover' CLI command."""

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_discover_basic(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {"catalog": {"db_path": "test.db"}}
        mock_pipeline = MagicMock()
        mock_pipeline.discover.return_value = 12
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["discover", "educational"])

        assert result.exit_code == 0
        assert "12" in result.output
        assert "educational" in result.output
        mock_pipeline.discover.assert_called_once_with("educational", max_results=50)

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_discover_with_limit(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.discover.return_value = 5
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["discover", "ads", "--limit", "10"])

        assert result.exit_code == 0
        mock_pipeline.discover.assert_called_once_with("ads", max_results=10)

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_discover_with_config(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.discover.return_value = 0
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["discover", "film", "--config", "/tmp/custom.yaml"])

        assert result.exit_code == 0
        mock_load.assert_called_once_with(Path("/tmp/custom.yaml"))

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_discover_empty_config_passes_none(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.discover.return_value = 0
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["discover", "nasa"])

        assert result.exit_code == 0
        mock_load.assert_called_once_with(None)


class TestProcessCommand:
    """Tests for the 'process' CLI command."""

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_batch(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.process_batch.return_value = [
            Path("/output/short1.mp4"),
            Path("/output/short2.mp4"),
        ]
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process"])

        assert result.exit_code == 0
        assert "2" in result.output
        mock_pipeline.process_batch.assert_called_once_with(category=None, batch_size=5)

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_batch_with_category_and_size(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.process_batch.return_value = []
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process", "--category", "film", "--batch", "10"])

        assert result.exit_code == 0
        mock_pipeline.process_batch.assert_called_once_with(category="film", batch_size=10)

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_single_identifier(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        item = _make_item("single-test")
        mock_pipeline._catalog.get_item.return_value = item
        mock_pipeline.process_single.return_value = Path("/output/single-test_short.mp4")
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process", "--identifier", "single-test"])

        assert result.exit_code == 0
        assert "Short created" in result.output
        mock_pipeline._catalog.get_item.assert_called_once_with("single-test")
        mock_pipeline.process_single.assert_called_once_with(item)

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_identifier_not_found(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline._catalog.get_item.return_value = None
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process", "--identifier", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_single_failure(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        item = _make_item("fail-test")
        mock_pipeline._catalog.get_item.return_value = item
        mock_pipeline.process_single.side_effect = RuntimeError("FFmpeg exploded")
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process", "--identifier", "fail-test"])

        assert result.exit_code == 1
        assert "Failed" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_with_config(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.process_batch.return_value = []
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process", "--config", "/tmp/custom.yaml"])

        assert result.exit_code == 0
        mock_load.assert_called_once_with(Path("/tmp/custom.yaml"))

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_process_empty_category_becomes_none(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.process_batch.return_value = []
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["process"])

        assert result.exit_code == 0
        mock_pipeline.process_batch.assert_called_once_with(category=None, batch_size=5)


class TestCatalogCommand:
    """Tests for the 'catalog' CLI command."""

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_catalog_basic_stats(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.get_stats.return_value = {
            "total": 50,
            "processed": 20,
            "unprocessed": 30,
            "by_category": {},
            "by_collection": {},
        }
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["catalog"])

        assert result.exit_code == 0
        assert "50" in result.output
        assert "20" in result.output
        assert "30" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_catalog_with_categories(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.get_stats.return_value = {
            "total": 10,
            "processed": 2,
            "unprocessed": 8,
            "by_category": {"ads": 4, "film": 6},
            "by_collection": {},
        }
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["catalog"])

        assert result.exit_code == 0
        assert "ads" in result.output
        assert "film" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_catalog_with_collections(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.get_stats.return_value = {
            "total": 15,
            "processed": 5,
            "unprocessed": 10,
            "by_category": {},
            "by_collection": {"prelinger": 10, "feature_films": 5},
        }
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["catalog"])

        assert result.exit_code == 0
        assert "prelinger" in result.output
        assert "feature_films" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_catalog_with_categories_and_collections(
        self, mock_load: MagicMock, mock_pipeline_cls: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.get_stats.return_value = {
            "total": 20,
            "processed": 8,
            "unprocessed": 12,
            "by_category": {"educational": 10, "nasa": 10},
            "by_collection": {"prelinger": 10, "nasa": 10},
        }
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["catalog"])

        assert result.exit_code == 0
        assert "educational" in result.output
        assert "nasa" in result.output
        assert "prelinger" in result.output

    @patch("timeless_clips.pipeline.TimelessClipsPipeline")
    @patch("timeless_clips.config.load_config")
    def test_catalog_with_config(self, mock_load: MagicMock, mock_pipeline_cls: MagicMock) -> None:
        mock_load.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.get_stats.return_value = {
            "total": 0,
            "processed": 0,
            "unprocessed": 0,
            "by_category": {},
            "by_collection": {},
        }
        mock_pipeline_cls.return_value = mock_pipeline

        result = runner.invoke(app, ["catalog", "--config", "/tmp/my.yaml"])

        assert result.exit_code == 0
        mock_load.assert_called_once_with(Path("/tmp/my.yaml"))


class TestInitCommand:
    """Tests for the 'init' CLI command."""

    def test_init_creates_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Created config" in result.output
        assert (tmp_path / "configs" / "config.yaml").exists()

    def test_init_creates_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "cache").exists()
        assert (tmp_path / "output").exists()

    def test_init_existing_config_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "configs" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("existing: true\n")

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Config exists" in result.output
        # Should NOT overwrite existing config
        assert config_path.read_text() == "existing: true\n"

    def test_init_custom_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        custom = tmp_path / "custom" / "settings.yaml"
        result = runner.invoke(app, ["init", "--config", str(custom)])
        assert result.exit_code == 0
        assert custom.exists()
        assert "Created config" in result.output

    def test_init_prints_completion_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Initialization complete" in result.output

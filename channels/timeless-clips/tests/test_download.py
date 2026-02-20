"""Tests for timeless_clips.download — MediaDownloader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from timeless_clips.download import MediaDownloader
from timeless_clips.models import ArchiveItem


def _make_item(**overrides) -> ArchiveItem:
    """Helper to build an ArchiveItem with sensible defaults."""
    defaults = {
        "identifier": "test-film-001",
        "title": "Test Film",
        "collection": "prelinger",
        "source_url": "https://archive.org/details/test-film-001",
        "download_urls": [
            "https://archive.org/download/test-film-001/film.mp4",
        ],
    }
    defaults.update(overrides)
    return ArchiveItem(**defaults)


def _zero_rate_config(tmp_path: Path) -> dict:
    """Config with rate_limit_seconds=0 and tmp_path cache."""
    return {
        "archive": {
            "rate_limit_seconds": 0,
            "cache_dir": str(tmp_path / "cache"),
            "preferred_formats": ["mp4", "ogv", "avi"],
        },
    }


class TestGetCachePath:
    """get_cache_path derives path from collection and identifier."""

    def test_cache_path_structure(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item(collection="prelinger", identifier="duck-cover")
        expected = tmp_path / "cache" / "prelinger" / "duck-cover"
        assert dl.get_cache_path(item) == expected

    def test_cache_path_different_collection(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item(collection="feature_films", identifier="noir-classic")
        expected = tmp_path / "cache" / "feature_films" / "noir-classic"
        assert dl.get_cache_path(item) == expected

    def test_cache_path_uses_config_dir(self, tmp_path: Path) -> None:
        config = {"archive": {"cache_dir": str(tmp_path / "custom"), "rate_limit_seconds": 0}}
        dl = MediaDownloader(config)
        item = _make_item()
        assert dl.get_cache_path(item).parent == tmp_path / "custom" / "prelinger"


class TestSelectBestUrl:
    """_select_best_url picks preferred formats, falls back to first."""

    def test_selects_mp4_first(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        urls = [
            "https://example.com/file.ogv",
            "https://example.com/file.mp4",
            "https://example.com/file.avi",
        ]
        assert dl._select_best_url(urls) == "https://example.com/file.mp4"

    def test_selects_ogv_when_no_mp4(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        urls = [
            "https://example.com/file.avi",
            "https://example.com/file.ogv",
        ]
        assert dl._select_best_url(urls) == "https://example.com/file.ogv"

    def test_selects_avi_when_no_mp4_ogv(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        urls = [
            "https://example.com/file.avi",
            "https://example.com/file.wmv",
        ]
        assert dl._select_best_url(urls) == "https://example.com/file.avi"

    def test_fallback_to_first_url(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        urls = [
            "https://example.com/file.wmv",
            "https://example.com/file.flv",
        ]
        assert dl._select_best_url(urls) == "https://example.com/file.wmv"

    def test_case_insensitive_extension(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        urls = ["https://example.com/file.MP4"]
        assert dl._select_best_url(urls) == "https://example.com/file.MP4"


class TestIsCached:
    """is_cached checks for existing files in cache directory."""

    def test_not_cached_no_directory(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item()
        assert dl.is_cached(item) is False

    def test_not_cached_empty_directory(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item()
        cache_path = dl.get_cache_path(item)
        cache_path.mkdir(parents=True)
        assert dl.is_cached(item) is False

    def test_cached_when_file_exists(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item()
        cache_path = dl.get_cache_path(item)
        cache_path.mkdir(parents=True)
        (cache_path / "film.mp4").write_bytes(b"fake video content")
        assert dl.is_cached(item) is True


class TestDownload:
    """download streams files, uses cache, integrates with catalog."""

    def _make_mock_client(self, content: bytes = b"video-data") -> MagicMock:
        """Create a mock httpx.Client with a working stream context manager."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [content]
        mock_response.raise_for_status = MagicMock()
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        return mock_client

    def test_download_fresh_file(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client(b"video-bytes")
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item()

        result = dl.download(item)

        assert result.exists()
        assert result.read_bytes() == b"video-bytes"
        assert result.name == "film.mp4"
        mock_client.stream.assert_called_once_with(
            "GET", "https://archive.org/download/test-film-001/film.mp4"
        )

    def test_download_uses_cache(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item()

        # Pre-populate cache
        cache_path = dl.get_cache_path(item)
        cache_path.mkdir(parents=True)
        cached_file = cache_path / "film.mp4"
        cached_file.write_bytes(b"cached-data")

        result = dl.download(item)

        assert result == cached_file
        assert result.read_bytes() == b"cached-data"
        mock_client.stream.assert_not_called()

    def test_download_no_urls_raises(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        dl = MediaDownloader(config)
        item = _make_item(download_urls=[])

        with pytest.raises(ValueError, match="No download URLs"):
            dl.download(item)

    def test_download_calls_catalog_set_local_path(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item()
        catalog = MagicMock()

        result = dl.download(item, catalog=catalog)

        catalog.set_local_path.assert_called_once_with(item.identifier, str(result))

    def test_download_without_catalog_no_error(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item()

        result = dl.download(item, catalog=None)
        assert result.exists()

    def test_download_extracts_filename_from_url(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item(download_urls=["https://archive.org/download/test-film-001/my_movie.ogv"])

        result = dl.download(item)
        assert result.name == "my_movie.ogv"

    def test_download_creates_cache_directory(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item()

        cache_dir = dl.get_cache_path(item)
        assert not cache_dir.exists()

        dl.download(item)

        assert cache_dir.exists()

    def test_download_selects_best_format(self, tmp_path: Path) -> None:
        config = _zero_rate_config(tmp_path)
        mock_client = self._make_mock_client()
        dl = MediaDownloader(config, client=mock_client)
        item = _make_item(
            download_urls=[
                "https://archive.org/download/test-film-001/film.ogv",
                "https://archive.org/download/test-film-001/film.mp4",
            ]
        )

        dl.download(item)

        mock_client.stream.assert_called_once_with(
            "GET", "https://archive.org/download/test-film-001/film.mp4"
        )


class TestThrottle:
    """_throttle enforces rate limiting between requests."""

    def test_throttle_sleeps_when_too_fast(self, tmp_path: Path) -> None:
        config = {"archive": {"rate_limit_seconds": 10.0, "cache_dir": str(tmp_path / "cache")}}
        dl = MediaDownloader(config)
        dl._last_request = 0.0  # Ancient timestamp

        with patch("timeless_clips.download.time.sleep") as mock_sleep:
            with patch("timeless_clips.download.time.monotonic", side_effect=[5.0, 5.0]):
                dl._throttle()
            # elapsed = 5.0 - 0.0 = 5.0 < 10.0, so should sleep 5.0
            mock_sleep.assert_called_once_with(5.0)

    def test_throttle_no_sleep_when_enough_time(self, tmp_path: Path) -> None:
        config = {"archive": {"rate_limit_seconds": 1.0, "cache_dir": str(tmp_path / "cache")}}
        dl = MediaDownloader(config)

        with patch("timeless_clips.download.time.sleep") as mock_sleep:
            with patch("timeless_clips.download.time.monotonic", side_effect=[100.0, 100.0]):
                dl._last_request = 0.0
                dl._throttle()
            mock_sleep.assert_not_called()


class TestMediaDownloaderDefaults:
    """Constructor defaults when config keys are missing."""

    def test_default_cache_dir(self) -> None:
        dl = MediaDownloader({})
        assert dl._cache_dir == Path("cache")

    def test_default_rate_limit(self) -> None:
        dl = MediaDownloader({})
        assert dl._rate_limit == 1.0

    def test_default_preferred_formats(self) -> None:
        dl = MediaDownloader({})
        assert dl._preferred == ["mp4", "ogv", "avi"]

    def test_custom_client_injected(self) -> None:
        mock_client = MagicMock()
        dl = MediaDownloader({}, client=mock_client)
        assert dl._client is mock_client

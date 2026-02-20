"""Shared fixtures for timeless-clips tests."""

from __future__ import annotations

import pytest

from timeless_clips.models import ArchiveItem, ShortScript, TextOverlay


@pytest.fixture()
def sample_item() -> ArchiveItem:
    """Return a fully populated ArchiveItem for testing."""
    return ArchiveItem(
        identifier="prelinger-1950-duck-cover",
        title="Duck and Cover (1951)",
        description="Civil defense film teaching children to duck and cover.",
        year=1951,
        collection="prelinger",
        media_type="movies",
        license_info="publicdomain",
        source_url="https://archive.org/details/prelinger-1950-duck-cover",
        download_urls=[
            "https://archive.org/download/prelinger-1950-duck-cover/duck_cover.mp4",
        ],
        duration=540.0,
        category="educational",
        tags=["cold-war", "civil-defense", "1950s"],
    )


@pytest.fixture()
def sample_script() -> ShortScript:
    """Return a ShortScript with overlays for testing."""
    return ShortScript(
        item_id="prelinger-1950-duck-cover",
        hook="They taught kids to hide under desks",
        start_time=30.0,
        end_time=55.0,
        narration="In 1951, the US government released a film teaching children to duck and cover.",
        text_overlays=[
            TextOverlay(time=2.0, text="1951", position="top-right"),
            TextOverlay(time=5.0, text="Duck and Cover"),
        ],
        closing="But did it actually work? Follow for more.",
        category="educational",
        mood="eerie",
        tags=["cold-war", "history"],
    )


@pytest.fixture()
def sample_config(tmp_path) -> dict:
    """Return a minimal config dict using tmp_path for directories."""
    return {
        "archive": {
            "base_url": "https://archive.org",
            "rate_limit_seconds": 1.0,
            "cache_dir": str(tmp_path / "cache"),
            "preferred_formats": ["mp4", "ogv", "avi"],
        },
        "llm": {
            "provider": "ollama",
            "model": "llama3.2",
            "host": "http://localhost:11434",
        },
        "tts": {
            "engine": "piper",
            "voice": "en_US-lessac-medium",
        },
        "captions": {
            "model": "base",
            "language": "en",
            "word_grouping": 3,
            "style": "white_outline",
        },
        "output": {
            "resolution": "1080x1920",
            "max_duration": 60,
            "format": "mp4",
            "codec": "libx264",
            "crf": 23,
            "output_dir": str(tmp_path / "output"),
        },
        "catalog": {
            "db_path": str(tmp_path / "catalog.db"),
        },
    }

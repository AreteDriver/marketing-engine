"""Pydantic v2 models for Timeless Clips pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TextOverlay(BaseModel):
    """A text overlay positioned at a specific time in the clip."""

    time: float  # seconds into the clip
    text: str
    position: str = "bottom"  # top, bottom, top-right, center


class ArchiveItem(BaseModel):
    """An Internet Archive item discovered for potential use."""

    identifier: str  # IA unique identifier
    title: str
    description: str = ""
    year: int | None = None
    collection: str  # prelinger, feature_films, etc.
    media_type: str = "movies"  # movies, audio, etc.
    license_info: str = "publicdomain"  # field name avoids shadowing builtin
    source_url: str  # https://archive.org/details/{identifier}
    download_urls: list[str] = []
    duration: float | None = None
    category: str = ""  # speech, film, ad, newsreel, educational, quote
    tags: list[str] = []
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed: bool = False


class ShortScript(BaseModel):
    """Script for a single YouTube Short generated from an archive clip."""

    item_id: str  # ArchiveItem.identifier
    hook: str  # Opening scroll-stopper (< 10 words)
    start_time: float  # seconds
    end_time: float  # seconds
    narration: str  # TTS text
    text_overlays: list[TextOverlay] = []
    closing: str  # CTA or cliffhanger
    category: str = ""
    mood: str = "nostalgic"  # nostalgic, dramatic, funny, eerie, inspiring
    tags: list[str] = []

    @property
    def duration(self) -> float:
        """Duration of the clip segment in seconds."""
        return self.end_time - self.start_time

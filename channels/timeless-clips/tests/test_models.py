"""Tests for timeless_clips.models — TextOverlay, ArchiveItem, ShortScript."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from timeless_clips.models import ArchiveItem, ShortScript, TextOverlay


class TestTextOverlay:
    """TextOverlay construction and defaults."""

    def test_required_fields(self) -> None:
        overlay = TextOverlay(time=3.5, text="Hello")
        assert overlay.time == 3.5
        assert overlay.text == "Hello"

    def test_default_position(self) -> None:
        overlay = TextOverlay(time=0.0, text="test")
        assert overlay.position == "bottom"

    def test_custom_position(self) -> None:
        overlay = TextOverlay(time=1.0, text="top text", position="top-right")
        assert overlay.position == "top-right"

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            TextOverlay(time=1.0)  # type: ignore[call-arg]

    def test_missing_time_raises(self) -> None:
        with pytest.raises(ValidationError):
            TextOverlay(text="no time")  # type: ignore[call-arg]


class TestArchiveItem:
    """ArchiveItem defaults, required fields, and serialization."""

    def test_minimal_construction(self) -> None:
        item = ArchiveItem(
            identifier="test-id",
            title="Test Film",
            collection="prelinger",
            source_url="https://archive.org/details/test-id",
        )
        assert item.identifier == "test-id"
        assert item.title == "Test Film"
        assert item.collection == "prelinger"
        assert item.source_url == "https://archive.org/details/test-id"

    def test_defaults(self) -> None:
        item = ArchiveItem(
            identifier="test-id",
            title="Test Film",
            collection="prelinger",
            source_url="https://archive.org/details/test-id",
        )
        assert item.description == ""
        assert item.year is None
        assert item.media_type == "movies"
        assert item.license_info == "publicdomain"
        assert item.download_urls == []
        assert item.duration is None
        assert item.category == ""
        assert item.tags == []
        assert item.processed is False

    def test_discovered_at_auto_set(self) -> None:
        before = datetime.now(UTC)
        item = ArchiveItem(
            identifier="ts-test",
            title="Timestamp Test",
            collection="test",
            source_url="https://archive.org/details/ts-test",
        )
        after = datetime.now(UTC)
        assert before <= item.discovered_at <= after

    def test_full_construction(self, sample_item: ArchiveItem) -> None:
        assert sample_item.identifier == "prelinger-1950-duck-cover"
        assert sample_item.year == 1951
        assert sample_item.duration == 540.0
        assert len(sample_item.download_urls) == 1
        assert sample_item.category == "educational"
        assert "cold-war" in sample_item.tags
        assert sample_item.processed is False

    def test_missing_required_identifier(self) -> None:
        with pytest.raises(ValidationError):
            ArchiveItem(
                title="No ID",
                collection="prelinger",
                source_url="https://archive.org/details/noid",
            )  # type: ignore[call-arg]

    def test_missing_required_title(self) -> None:
        with pytest.raises(ValidationError):
            ArchiveItem(
                identifier="no-title",
                collection="prelinger",
                source_url="https://archive.org/details/no-title",
            )  # type: ignore[call-arg]

    def test_missing_required_collection(self) -> None:
        with pytest.raises(ValidationError):
            ArchiveItem(
                identifier="no-coll",
                title="No Collection",
                source_url="https://archive.org/details/no-coll",
            )  # type: ignore[call-arg]

    def test_missing_required_source_url(self) -> None:
        with pytest.raises(ValidationError):
            ArchiveItem(
                identifier="no-url",
                title="No URL",
                collection="prelinger",
            )  # type: ignore[call-arg]

    def test_serialization_roundtrip(self, sample_item: ArchiveItem) -> None:
        data = sample_item.model_dump()
        restored = ArchiveItem(**data)
        assert restored.identifier == sample_item.identifier
        assert restored.title == sample_item.title
        assert restored.year == sample_item.year
        assert restored.tags == sample_item.tags
        assert restored.discovered_at == sample_item.discovered_at

    def test_model_dump_contains_all_fields(self, sample_item: ArchiveItem) -> None:
        data = sample_item.model_dump()
        expected_keys = {
            "identifier",
            "title",
            "description",
            "year",
            "collection",
            "media_type",
            "license_info",
            "source_url",
            "download_urls",
            "duration",
            "category",
            "tags",
            "discovered_at",
            "processed",
        }
        assert set(data.keys()) == expected_keys

    def test_json_roundtrip(self, sample_item: ArchiveItem) -> None:
        json_str = sample_item.model_dump_json()
        restored = ArchiveItem.model_validate_json(json_str)
        assert restored.identifier == sample_item.identifier
        assert restored.year == sample_item.year

    def test_processed_flag(self) -> None:
        item = ArchiveItem(
            identifier="proc-test",
            title="Processed Test",
            collection="test",
            source_url="https://archive.org/details/proc-test",
            processed=True,
        )
        assert item.processed is True


class TestShortScript:
    """ShortScript construction, defaults, and duration property."""

    def test_minimal_construction(self) -> None:
        script = ShortScript(
            item_id="test-id",
            hook="Watch this",
            start_time=0.0,
            end_time=30.0,
            narration="A narration.",
            closing="Follow for more.",
        )
        assert script.item_id == "test-id"
        assert script.hook == "Watch this"
        assert script.start_time == 0.0
        assert script.end_time == 30.0
        assert script.narration == "A narration."
        assert script.closing == "Follow for more."

    def test_defaults(self) -> None:
        script = ShortScript(
            item_id="test-id",
            hook="Hook",
            start_time=0.0,
            end_time=10.0,
            narration="Narration.",
            closing="CTA.",
        )
        assert script.text_overlays == []
        assert script.category == ""
        assert script.mood == "nostalgic"
        assert script.tags == []

    def test_duration_property(self) -> None:
        script = ShortScript(
            item_id="dur-test",
            hook="Hook",
            start_time=10.0,
            end_time=45.5,
            narration="Narration.",
            closing="End.",
        )
        assert script.duration == pytest.approx(35.5)

    def test_duration_zero(self) -> None:
        script = ShortScript(
            item_id="zero-dur",
            hook="Hook",
            start_time=5.0,
            end_time=5.0,
            narration="Empty.",
            closing="End.",
        )
        assert script.duration == 0.0

    def test_full_construction(self, sample_script: ShortScript) -> None:
        assert sample_script.item_id == "prelinger-1950-duck-cover"
        assert sample_script.mood == "eerie"
        assert len(sample_script.text_overlays) == 2
        assert sample_script.text_overlays[0].position == "top-right"
        assert sample_script.text_overlays[1].position == "bottom"  # default
        assert sample_script.duration == pytest.approx(25.0)

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ShortScript(
                item_id="test",
                hook="Hook",
            )  # type: ignore[call-arg]

    def test_serialization_roundtrip(self, sample_script: ShortScript) -> None:
        data = sample_script.model_dump()
        restored = ShortScript(**data)
        assert restored.item_id == sample_script.item_id
        assert restored.hook == sample_script.hook
        assert restored.duration == sample_script.duration
        assert len(restored.text_overlays) == len(sample_script.text_overlays)

    def test_model_dump_excludes_duration(self, sample_script: ShortScript) -> None:
        """Duration is a @property, not a field — it should not appear in model_dump."""
        data = sample_script.model_dump()
        assert "duration" not in data

    def test_custom_mood(self) -> None:
        script = ShortScript(
            item_id="mood-test",
            hook="Hook",
            start_time=0.0,
            end_time=10.0,
            narration="Narration.",
            closing="End.",
            mood="dramatic",
        )
        assert script.mood == "dramatic"

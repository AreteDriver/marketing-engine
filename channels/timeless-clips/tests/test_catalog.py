"""Tests for the SQLite catalog module."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from timeless_clips.catalog import Catalog
from timeless_clips.models import ArchiveItem


@pytest.fixture()
def make_item():
    """Factory fixture to create ArchiveItems with sensible defaults."""
    _counter = 0

    def _factory(**overrides) -> ArchiveItem:
        nonlocal _counter
        _counter += 1
        defaults = {
            "identifier": f"item-{_counter}",
            "title": f"Test Item {_counter}",
            "description": "A test archive item.",
            "year": 1950,
            "collection": "prelinger",
            "media_type": "movies",
            "license_info": "publicdomain",
            "source_url": f"https://archive.org/details/item-{_counter}",
            "download_urls": [f"https://archive.org/download/item-{_counter}/video.mp4"],
            "duration": 120.0,
            "category": "educational",
            "tags": ["test", "archive"],
        }
        defaults.update(overrides)
        return ArchiveItem(**defaults)

    return _factory


@pytest.fixture()
def catalog(tmp_path) -> Catalog:
    """Create a Catalog backed by a temp SQLite file."""
    cat = Catalog(tmp_path / "test.db")
    yield cat
    cat.close()


class TestCatalogInit:
    """Tests for Catalog initialization."""

    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "sub" / "deep" / "catalog.db"
        cat = Catalog(db_path)
        assert db_path.exists()
        cat.close()

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "catalog.db"
        cat = Catalog(nested)
        assert nested.parent.is_dir()
        cat.close()

    def test_schema_tables_exist(self, tmp_path):
        db_path = tmp_path / "schema.db"
        cat = Catalog(db_path)
        conn = sqlite3.connect(str(db_path))
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "catalog" in table_names
        conn.close()
        cat.close()

    def test_schema_indexes_exist(self, tmp_path):
        db_path = tmp_path / "idx.db"
        cat = Catalog(db_path)
        conn = sqlite3.connect(str(db_path))
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        index_names = {i[0] for i in indexes}
        assert "idx_catalog_category" in index_names
        assert "idx_catalog_processed" in index_names
        assert "idx_catalog_collection" in index_names
        conn.close()
        cat.close()

    def test_accepts_path_object(self, tmp_path):
        cat = Catalog(Path(tmp_path / "path_obj.db"))
        assert cat._db_path == str(tmp_path / "path_obj.db")
        cat.close()

    def test_accepts_string_path(self, tmp_path):
        cat = Catalog(str(tmp_path / "str_path.db"))
        assert cat._db_path == str(tmp_path / "str_path.db")
        cat.close()

    def test_wal_journal_mode(self, catalog):
        conn = catalog._get_conn()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_row_factory_set(self, catalog):
        conn = catalog._get_conn()
        assert conn.row_factory is sqlite3.Row


class TestSaveItem:
    """Tests for Catalog.save_item."""

    def test_save_and_retrieve(self, catalog, make_item):
        item = make_item(identifier="save-test")
        catalog.save_item(item)
        result = catalog.get_item("save-test")
        assert result is not None
        assert result.identifier == "save-test"
        assert result.title == item.title

    def test_save_stores_all_fields(self, catalog, make_item):
        item = make_item(
            identifier="full-fields",
            title="Full Fields Test",
            description="All fields populated.",
            year=1962,
            collection="feature_films",
            media_type="movies",
            license_info="publicdomain",
            source_url="https://archive.org/details/full-fields",
            download_urls=["https://archive.org/download/full-fields/a.mp4"],
            duration=300.5,
            category="film",
            tags=["drama", "classic"],
        )
        catalog.save_item(item)
        result = catalog.get_item("full-fields")
        assert result.title == "Full Fields Test"
        assert result.description == "All fields populated."
        assert result.year == 1962
        assert result.collection == "feature_films"
        assert result.media_type == "movies"
        assert result.license_info == "publicdomain"
        assert result.source_url == "https://archive.org/details/full-fields"
        assert result.download_urls == ["https://archive.org/download/full-fields/a.mp4"]
        assert result.duration == 300.5
        assert result.category == "film"
        assert result.tags == ["drama", "classic"]
        assert result.processed is False

    def test_save_with_metadata(self, catalog, make_item):
        item = make_item(identifier="meta-item")
        metadata = {"extra_key": "extra_value", "files_count": 3}
        catalog.save_item(item, metadata=metadata)
        # Verify metadata is stored in DB
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT metadata FROM catalog WHERE identifier = ?", ("meta-item",)
        ).fetchone()
        stored = json.loads(row["metadata"])
        assert stored == metadata

    def test_save_without_metadata_stores_empty_dict(self, catalog, make_item):
        item = make_item(identifier="no-meta")
        catalog.save_item(item)
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT metadata FROM catalog WHERE identifier = ?", ("no-meta",)
        ).fetchone()
        assert json.loads(row["metadata"]) == {}

    def test_upsert_replaces_existing(self, catalog, make_item):
        item = make_item(identifier="upsert-me", title="Original")
        catalog.save_item(item)
        updated = make_item(identifier="upsert-me", title="Updated")
        catalog.save_item(updated)
        result = catalog.get_item("upsert-me")
        assert result.title == "Updated"

    def test_upsert_preserves_single_row(self, catalog, make_item):
        item = make_item(identifier="single-row")
        catalog.save_item(item)
        catalog.save_item(make_item(identifier="single-row", title="V2"))
        catalog.save_item(make_item(identifier="single-row", title="V3"))
        conn = catalog._get_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM catalog WHERE identifier = ?", ("single-row",)
        ).fetchone()[0]
        assert count == 1

    def test_save_item_with_none_year(self, catalog, make_item):
        item = make_item(identifier="no-year", year=None)
        catalog.save_item(item)
        result = catalog.get_item("no-year")
        assert result.year is None

    def test_save_item_with_none_duration(self, catalog, make_item):
        item = make_item(identifier="no-dur", duration=None)
        catalog.save_item(item)
        result = catalog.get_item("no-dur")
        assert result.duration is None

    def test_save_item_with_empty_tags(self, catalog, make_item):
        item = make_item(identifier="no-tags", tags=[])
        catalog.save_item(item)
        result = catalog.get_item("no-tags")
        assert result.tags == []

    def test_save_item_with_empty_download_urls(self, catalog, make_item):
        item = make_item(identifier="no-urls", download_urls=[])
        catalog.save_item(item)
        result = catalog.get_item("no-urls")
        assert result.download_urls == []


class TestGetItem:
    """Tests for Catalog.get_item."""

    def test_get_existing(self, catalog, make_item):
        item = make_item(identifier="exists")
        catalog.save_item(item)
        result = catalog.get_item("exists")
        assert result is not None
        assert result.identifier == "exists"

    def test_get_nonexistent_returns_none(self, catalog):
        assert catalog.get_item("does-not-exist") is None

    def test_discovered_at_roundtrip(self, catalog, make_item):
        now = datetime.now(UTC)
        item = make_item(identifier="time-test", discovered_at=now)
        # Pydantic may store the field on the model as-is
        catalog.save_item(item)
        result = catalog.get_item("time-test")
        assert result.discovered_at.year == now.year
        assert result.discovered_at.month == now.month
        assert result.discovered_at.day == now.day


class TestGetUnprocessed:
    """Tests for Catalog.get_unprocessed."""

    def test_returns_unprocessed_only(self, catalog, make_item):
        catalog.save_item(make_item(identifier="a", processed=False))
        catalog.save_item(make_item(identifier="b", processed=True))
        catalog.save_item(make_item(identifier="c", processed=False))
        items = catalog.get_unprocessed()
        ids = {i.identifier for i in items}
        assert "a" in ids
        assert "c" in ids
        assert "b" not in ids

    def test_filter_by_category(self, catalog, make_item):
        catalog.save_item(make_item(identifier="edu1", category="educational"))
        catalog.save_item(make_item(identifier="film1", category="film"))
        catalog.save_item(make_item(identifier="edu2", category="educational"))
        items = catalog.get_unprocessed(category="educational")
        assert len(items) == 2
        assert all(i.category == "educational" for i in items)

    def test_no_category_returns_all_unprocessed(self, catalog, make_item):
        catalog.save_item(make_item(identifier="x", category="ads"))
        catalog.save_item(make_item(identifier="y", category="film"))
        items = catalog.get_unprocessed()
        assert len(items) == 2

    def test_limit_respected(self, catalog, make_item):
        for i in range(5):
            catalog.save_item(make_item(identifier=f"lim-{i}"))
        items = catalog.get_unprocessed(limit=3)
        assert len(items) == 3

    def test_empty_catalog_returns_empty(self, catalog):
        assert catalog.get_unprocessed() == []

    def test_all_processed_returns_empty(self, catalog, make_item):
        catalog.save_item(make_item(identifier="done1", processed=True))
        catalog.save_item(make_item(identifier="done2", processed=True))
        assert catalog.get_unprocessed() == []


class TestMarkProcessed:
    """Tests for Catalog.mark_processed."""

    def test_marks_item_as_processed(self, catalog, make_item):
        catalog.save_item(make_item(identifier="mark-me"))
        catalog.mark_processed("mark-me")
        result = catalog.get_item("mark-me")
        assert result.processed is True

    def test_sets_processed_at_timestamp(self, catalog, make_item):
        catalog.save_item(make_item(identifier="ts-check"))
        catalog.mark_processed("ts-check")
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT processed_at FROM catalog WHERE identifier = ?", ("ts-check",)
        ).fetchone()
        assert row["processed_at"] is not None
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(row["processed_at"])
        assert dt.year >= 2024

    def test_sets_short_path(self, catalog, make_item):
        catalog.save_item(make_item(identifier="sp-test"))
        catalog.mark_processed("sp-test", short_path="/output/shorts/sp-test.mp4")
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT short_path FROM catalog WHERE identifier = ?", ("sp-test",)
        ).fetchone()
        assert row["short_path"] == "/output/shorts/sp-test.mp4"

    def test_short_path_none_by_default(self, catalog, make_item):
        catalog.save_item(make_item(identifier="no-sp"))
        catalog.mark_processed("no-sp")
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT short_path FROM catalog WHERE identifier = ?", ("no-sp",)
        ).fetchone()
        assert row["short_path"] is None

    def test_no_longer_in_unprocessed(self, catalog, make_item):
        catalog.save_item(make_item(identifier="gone"))
        catalog.mark_processed("gone")
        items = catalog.get_unprocessed()
        assert all(i.identifier != "gone" for i in items)


class TestSetLocalPath:
    """Tests for Catalog.set_local_path."""

    def test_sets_local_path(self, catalog, make_item):
        catalog.save_item(make_item(identifier="dl-test"))
        catalog.set_local_path("dl-test", "/tmp/downloads/dl-test.mp4")
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT local_path FROM catalog WHERE identifier = ?", ("dl-test",)
        ).fetchone()
        assert row["local_path"] == "/tmp/downloads/dl-test.mp4"

    def test_overwrite_local_path(self, catalog, make_item):
        catalog.save_item(make_item(identifier="overwrite"))
        catalog.set_local_path("overwrite", "/first/path.mp4")
        catalog.set_local_path("overwrite", "/second/path.mp4")
        conn = catalog._get_conn()
        row = conn.execute(
            "SELECT local_path FROM catalog WHERE identifier = ?", ("overwrite",)
        ).fetchone()
        assert row["local_path"] == "/second/path.mp4"


class TestGetStats:
    """Tests for Catalog.get_stats."""

    def test_empty_catalog_stats(self, catalog):
        stats = catalog.get_stats()
        assert stats["total"] == 0
        assert stats["processed"] == 0
        assert stats["unprocessed"] == 0
        assert stats["by_category"] == {}
        assert stats["by_collection"] == {}

    def test_populated_stats(self, catalog, make_item):
        catalog.save_item(make_item(identifier="s1", category="ads", collection="prelinger"))
        catalog.save_item(make_item(identifier="s2", category="ads", collection="prelinger"))
        catalog.save_item(make_item(identifier="s3", category="film", collection="feature_films"))
        catalog.save_item(
            make_item(identifier="s4", category="film", collection="feature_films", processed=True)
        )
        stats = catalog.get_stats()
        assert stats["total"] == 4
        assert stats["processed"] == 1
        assert stats["unprocessed"] == 3
        assert stats["by_category"] == {"ads": 2, "film": 2}
        assert stats["by_collection"] == {"prelinger": 2, "feature_films": 2}

    def test_stats_after_mark_processed(self, catalog, make_item):
        catalog.save_item(make_item(identifier="p1"))
        catalog.save_item(make_item(identifier="p2"))
        catalog.mark_processed("p1")
        stats = catalog.get_stats()
        assert stats["processed"] == 1
        assert stats["unprocessed"] == 1


class TestClose:
    """Tests for Catalog.close."""

    def test_close_clears_connection(self, tmp_path, make_item):
        cat = Catalog(tmp_path / "close.db")
        # Ensure connection is established
        cat.save_item(make_item(identifier="before-close"))
        cat.close()
        assert getattr(cat._local, "conn", None) is None

    def test_close_when_no_connection(self, tmp_path):
        """Closing without any prior DB operation should not raise."""
        cat = Catalog(tmp_path / "no-conn.db")
        # _init_schema creates a connection, so close it first, then close again
        cat.close()
        # Second close should be safe
        cat.close()

    def test_get_conn_creates_new_after_close(self, tmp_path, make_item):
        cat = Catalog(tmp_path / "reopen.db")
        cat.save_item(make_item(identifier="first"))
        cat.close()
        # Should be able to use catalog again (new connection)
        cat.save_item(make_item(identifier="second"))
        result = cat.get_item("second")
        assert result is not None
        cat.close()

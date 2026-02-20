"""Tests for the Internet Archive content discovery module."""

from __future__ import annotations

import logging
from unittest.mock import patch

import httpx
import pytest

from timeless_clips.catalog import Catalog
from timeless_clips.discover import (
    _ALLOWED_LICENSES,
    QUERIES,
    ContentDiscoverer,
)
from timeless_clips.models import ArchiveItem

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
            "download_urls": [],
            "duration": 120.0,
            "category": "educational",
            "tags": ["test"],
        }
        defaults.update(overrides)
        return ArchiveItem(**defaults)

    return _factory


def _make_search_response(docs: list[dict]) -> dict:
    """Build an IA advanced search JSON response body."""
    return {"response": {"docs": docs}}


def _make_transport(responses: dict[str, httpx.Response]) -> httpx.MockTransport:
    """Create a MockTransport that routes by URL prefix.

    ``responses`` maps a URL substring to the httpx.Response to return.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for pattern, resp in responses.items():
            if pattern in url:
                return resp
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def _discoverer(
    transport: httpx.MockTransport | None = None,
    config: dict | None = None,
) -> ContentDiscoverer:
    """Build a ContentDiscoverer with rate limiting disabled."""
    cfg = config or {}
    cfg.setdefault("archive", {})
    cfg["archive"]["rate_limit_seconds"] = 0
    client = httpx.Client(transport=transport) if transport else None
    return ContentDiscoverer(cfg, client=client)


# ---------------------------------------------------------------------------
# ContentDiscoverer.__init__
# ---------------------------------------------------------------------------


class TestContentDiscovererInit:
    """Tests for ContentDiscoverer construction."""

    def test_default_rate_limit(self):
        d = ContentDiscoverer({})
        assert d._rate_limit == 1.0

    def test_custom_rate_limit(self):
        d = ContentDiscoverer({"archive": {"rate_limit_seconds": 2.5}})
        assert d._rate_limit == 2.5

    def test_creates_client_when_none_given(self):
        d = ContentDiscoverer({})
        assert isinstance(d._client, httpx.Client)

    def test_uses_provided_client(self):
        client = httpx.Client()
        d = ContentDiscoverer({}, client=client)
        assert d._client is client


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------


class TestThrottle:
    """Tests for the rate-limiting throttle."""

    def test_throttle_does_not_sleep_when_rate_limit_zero(self):
        d = _discoverer()
        with patch("timeless_clips.discover.time.sleep") as mock_sleep:
            d._throttle()
            d._throttle()
            mock_sleep.assert_not_called()

    def test_throttle_sleeps_when_needed(self):
        d = ContentDiscoverer({"archive": {"rate_limit_seconds": 10.0}})
        d._last_request = 1e18  # far future to guarantee elapsed > rate_limit first call
        d._last_request = 0.0
        # Force _last_request to current time so next call must sleep
        import time

        d._last_request = time.monotonic()
        with patch("timeless_clips.discover.time.sleep") as mock_sleep:
            d._throttle()
            mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    """Tests for ContentDiscoverer.search."""

    def test_basic_search(self):
        doc = {
            "identifier": "test-film",
            "title": "Test Film",
            "description": "A test film",
            "year": 1920,
            "licenseurl": "publicdomain",
            "collection": "prelinger",
        }
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("test query", max_results=10)
        assert len(items) == 1
        assert items[0].identifier == "test-film"
        assert items[0].title == "Test Film"
        assert items[0].year == 1920
        assert items[0].collection == "prelinger"
        assert items[0].license_info == "publicdomain"

    def test_collection_as_list(self):
        doc = {
            "identifier": "multi-coll",
            "title": "Multi",
            "collection": ["prelinger", "feature_films"],
        }
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].collection == "prelinger"

    def test_collection_as_empty_list(self):
        doc = {
            "identifier": "empty-coll",
            "title": "Empty Coll",
            "collection": [],
        }
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].collection == ""

    def test_collection_as_string(self):
        doc = {
            "identifier": "str-coll",
            "title": "Str Coll",
            "collection": "nasa",
        }
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].collection == "nasa"

    def test_empty_results(self):
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([])),
            }
        )
        d = _discoverer(transport)
        items = d.search("nothing")
        assert items == []

    def test_missing_fields_use_defaults(self):
        doc = {"identifier": "bare-min"}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].identifier == "bare-min"
        assert items[0].title == "Unknown"
        assert items[0].description == ""
        assert items[0].year is None
        assert items[0].license_info == ""
        assert items[0].collection == ""

    def test_year_zero_treated_as_none(self):
        doc = {"identifier": "y0", "title": "Year Zero", "year": 0, "collection": "x"}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].year is None

    def test_year_none_treated_as_none(self):
        doc = {"identifier": "yn", "title": "Year None", "year": None, "collection": "x"}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].year is None

    def test_source_url_constructed(self):
        doc = {"identifier": "url-test", "collection": "c"}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search("query")
        assert items[0].source_url == "https://archive.org/details/url-test"

    def test_multiple_results(self):
        docs = [
            {"identifier": f"multi-{i}", "title": f"Film {i}", "collection": "c"} for i in range(5)
        ]
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response(docs)),
            }
        )
        d = _discoverer(transport)
        items = d.search("query", max_results=5)
        assert len(items) == 5

    def test_http_error_propagates(self):
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(500, text="Server Error"),
            }
        )
        d = _discoverer(transport)
        with pytest.raises(httpx.HTTPStatusError):
            d.search("query")


# ---------------------------------------------------------------------------
# search_category
# ---------------------------------------------------------------------------


class TestSearchCategory:
    """Tests for ContentDiscoverer.search_category."""

    def test_valid_category(self):
        doc = {"identifier": "ad-item", "title": "Vintage Ad", "collection": "prelinger"}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response([doc])),
            }
        )
        d = _discoverer(transport)
        items = d.search_category("ads", max_results=10)
        assert len(items) == 1
        assert items[0].category == "ads"

    def test_sets_category_on_all_items(self):
        docs = [
            {"identifier": f"edu-{i}", "title": f"Edu {i}", "collection": "prelinger"}
            for i in range(3)
        ]
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response(docs)),
            }
        )
        d = _discoverer(transport)
        items = d.search_category("educational")
        assert all(item.category == "educational" for item in items)

    def test_invalid_category_raises(self):
        d = _discoverer()
        with pytest.raises(ValueError, match="Unknown category: bogus"):
            d.search_category("bogus")

    def test_all_predefined_categories_exist(self):
        expected = {"ads", "educational", "film", "speech", "nasa", "newsreel"}
        assert set(QUERIES.keys()) == expected


# ---------------------------------------------------------------------------
# filter_usable
# ---------------------------------------------------------------------------


class TestFilterUsable:
    """Tests for ContentDiscoverer.filter_usable."""

    def test_public_domain_passes(self, make_item):
        d = _discoverer()
        items = [make_item(license_info="publicdomain")]
        assert len(d.filter_usable(items)) == 1

    def test_empty_license_passes(self, make_item):
        d = _discoverer()
        items = [make_item(license_info="")]
        assert len(d.filter_usable(items)) == 1

    def test_cc_by_passes(self, make_item):
        d = _discoverer()
        items = [make_item(license_info="http://creativecommons.org/licenses/by/4.0/")]
        assert len(d.filter_usable(items)) == 1

    def test_cc_zero_passes(self, make_item):
        d = _discoverer()
        items = [make_item(license_info="https://creativecommons.org/publicdomain/zero/1.0/")]
        assert len(d.filter_usable(items)) == 1

    def test_restrictive_license_rejected(self, make_item):
        d = _discoverer()
        items = [make_item(license_info="http://creativecommons.org/licenses/by-nc-nd/4.0/")]
        assert len(d.filter_usable(items)) == 0

    def test_mixed_licenses(self, make_item):
        d = _discoverer()
        items = [
            make_item(license_info="publicdomain"),
            make_item(license_info="http://creativecommons.org/licenses/by-nc/4.0/"),
            make_item(license_info="Public Domain"),
        ]
        result = d.filter_usable(items)
        assert len(result) == 2

    def test_empty_list(self):
        d = _discoverer()
        assert d.filter_usable([]) == []

    def test_all_allowed_licenses_pass(self, make_item):
        d = _discoverer()
        items = [make_item(license_info=lic) for lic in _ALLOWED_LICENSES]
        result = d.filter_usable(items)
        assert len(result) == len(_ALLOWED_LICENSES)


# ---------------------------------------------------------------------------
# get_metadata
# ---------------------------------------------------------------------------


class TestGetMetadata:
    """Tests for ContentDiscoverer.get_metadata."""

    def test_returns_metadata_json(self):
        meta = {"metadata": {"title": "Test"}, "files": []}
        transport = _make_transport(
            {
                "metadata": httpx.Response(200, json=meta),
            }
        )
        d = _discoverer(transport)
        result = d.get_metadata("test-id")
        assert result == meta

    def test_http_error_propagates(self):
        transport = _make_transport(
            {
                "metadata": httpx.Response(404, text="Not Found"),
            }
        )
        d = _discoverer(transport)
        with pytest.raises(httpx.HTTPStatusError):
            d.get_metadata("missing-id")


# ---------------------------------------------------------------------------
# enrich_item
# ---------------------------------------------------------------------------


class TestEnrichItem:
    """Tests for ContentDiscoverer.enrich_item."""

    def test_adds_download_urls(self, make_item):
        d = _discoverer()
        item = make_item(identifier="enrich-dl", download_urls=[])
        metadata = {
            "files": [
                {"name": "video.mp4"},
                {"name": "video.ogv"},
                {"name": "thumbnail.jpg"},
            ],
            "metadata": {},
        }
        result = d.enrich_item(item, metadata)
        assert "https://archive.org/download/enrich-dl/video.mp4" in result.download_urls
        assert "https://archive.org/download/enrich-dl/video.ogv" in result.download_urls
        # jpg not in preferred formats
        assert all("thumbnail.jpg" not in u for u in result.download_urls)

    def test_preferred_format_order(self, make_item):
        """mp4 files come before ogv files (format ordering)."""
        d = _discoverer()
        item = make_item(identifier="order-test", download_urls=[])
        metadata = {
            "files": [
                {"name": "z_video.ogv"},
                {"name": "a_video.mp4"},
            ],
            "metadata": {},
        }
        result = d.enrich_item(item, metadata)
        # mp4 is first in preferred_formats, so its URLs come first
        mp4_idx = next(i for i, u in enumerate(result.download_urls) if u.endswith(".mp4"))
        ogv_idx = next(i for i, u in enumerate(result.download_urls) if u.endswith(".ogv"))
        assert mp4_idx < ogv_idx

    def test_custom_preferred_formats(self, make_item):
        d = _discoverer(config={"archive": {"preferred_formats": ["avi"]}})
        item = make_item(identifier="avi-test", download_urls=[])
        metadata = {
            "files": [
                {"name": "video.mp4"},
                {"name": "video.avi"},
            ],
            "metadata": {},
        }
        result = d.enrich_item(item, metadata)
        assert len(result.download_urls) == 1
        assert result.download_urls[0].endswith(".avi")

    def test_year_enrichment_when_missing(self, make_item):
        d = _discoverer()
        item = make_item(identifier="year-enrich", year=None)
        metadata = {"files": [], "metadata": {"year": "1945"}}
        result = d.enrich_item(item, metadata)
        assert result.year == 1945

    def test_year_not_overwritten_when_present(self, make_item):
        d = _discoverer()
        item = make_item(identifier="year-keep", year=1960)
        metadata = {"files": [], "metadata": {"year": "1945"}}
        result = d.enrich_item(item, metadata)
        assert result.year == 1960

    def test_year_invalid_suppressed(self, make_item):
        d = _discoverer()
        item = make_item(identifier="year-bad", year=None)
        metadata = {"files": [], "metadata": {"year": "not-a-number"}}
        result = d.enrich_item(item, metadata)
        assert result.year is None

    def test_year_none_in_metadata_suppressed(self, make_item):
        """TypeError from int(None) should be suppressed."""
        d = _discoverer()
        item = make_item(identifier="year-none-meta", year=None)
        metadata = {"files": [], "metadata": {"year": None}}
        result = d.enrich_item(item, metadata)
        assert result.year is None

    def test_description_enrichment_when_missing(self, make_item):
        d = _discoverer()
        item = make_item(identifier="desc-enrich", description="")
        metadata = {"files": [], "metadata": {"description": "Enriched description."}}
        result = d.enrich_item(item, metadata)
        assert result.description == "Enriched description."

    def test_description_not_overwritten_when_present(self, make_item):
        d = _discoverer()
        item = make_item(identifier="desc-keep", description="Original")
        metadata = {"files": [], "metadata": {"description": "New"}}
        result = d.enrich_item(item, metadata)
        assert result.description == "Original"

    def test_description_non_string_converted(self, make_item):
        d = _discoverer()
        item = make_item(identifier="desc-list", description="")
        metadata = {"files": [], "metadata": {"description": ["line1", "line2"]}}
        result = d.enrich_item(item, metadata)
        assert result.description == "['line1', 'line2']"

    def test_no_files_in_metadata(self, make_item):
        d = _discoverer()
        item = make_item(identifier="no-files", download_urls=[])
        metadata = {"metadata": {}}
        result = d.enrich_item(item, metadata)
        assert result.download_urls == []

    def test_case_insensitive_extension_match(self, make_item):
        d = _discoverer()
        item = make_item(identifier="case-ext", download_urls=[])
        metadata = {
            "files": [{"name": "VIDEO.MP4"}, {"name": "clip.OGV"}],
            "metadata": {},
        }
        result = d.enrich_item(item, metadata)
        assert len(result.download_urls) == 2


# ---------------------------------------------------------------------------
# discover_and_catalog
# ---------------------------------------------------------------------------


class TestDiscoverAndCatalog:
    """Tests for ContentDiscoverer.discover_and_catalog."""

    def _build_discoverer_and_catalog(self, tmp_path, search_docs, metadata_resp=None):
        """Helper to build discoverer with search + metadata mocks."""
        meta = metadata_resp or {"files": [], "metadata": {}}
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response(search_docs)),
                "metadata": httpx.Response(200, json=meta),
            }
        )
        d = _discoverer(transport)
        cat = Catalog(tmp_path / "catalog.db")
        return d, cat

    def test_happy_path(self, tmp_path):
        docs = [
            {
                "identifier": "new-item",
                "title": "New Item",
                "collection": "prelinger",
                "licenseurl": "publicdomain",
            },
        ]
        d, cat = self._build_discoverer_and_catalog(tmp_path, docs)
        count = d.discover_and_catalog(cat, "ads", max_results=10)
        assert count == 1
        assert cat.get_item("new-item") is not None
        cat.close()

    def test_skips_already_cataloged(self, tmp_path, make_item):
        docs = [
            {
                "identifier": "existing",
                "title": "Already There",
                "collection": "prelinger",
                "licenseurl": "publicdomain",
            },
        ]
        d, cat = self._build_discoverer_and_catalog(tmp_path, docs)
        # Pre-seed the catalog
        cat.save_item(make_item(identifier="existing"))
        count = d.discover_and_catalog(cat, "ads")
        assert count == 0
        cat.close()

    def test_filters_unusable_licenses(self, tmp_path):
        docs = [
            {
                "identifier": "nc-item",
                "title": "Non-Commercial",
                "collection": "prelinger",
                "licenseurl": "http://creativecommons.org/licenses/by-nc/4.0/",
            },
        ]
        d, cat = self._build_discoverer_and_catalog(tmp_path, docs)
        count = d.discover_and_catalog(cat, "ads")
        assert count == 0
        assert cat.get_item("nc-item") is None
        cat.close()

    def test_metadata_fetch_failure_skips_item(self, tmp_path, caplog):
        docs = [
            {
                "identifier": "fail-meta",
                "title": "Will Fail",
                "collection": "prelinger",
                "licenseurl": "publicdomain",
            },
        ]
        transport = _make_transport(
            {
                "advancedsearch": httpx.Response(200, json=_make_search_response(docs)),
                "metadata": httpx.Response(500, text="Server Error"),
            }
        )
        d = _discoverer(transport)
        cat = Catalog(tmp_path / "catalog.db")
        with caplog.at_level(logging.WARNING, logger="timeless_clips.discover"):
            count = d.discover_and_catalog(cat, "ads")
        assert count == 0
        assert cat.get_item("fail-meta") is None
        assert "Failed to fetch metadata" in caplog.text
        cat.close()

    def test_multiple_items_mixed(self, tmp_path):
        docs = [
            {
                "identifier": "good-1",
                "title": "Good 1",
                "collection": "prelinger",
                "licenseurl": "publicdomain",
            },
            {
                "identifier": "bad-lic",
                "title": "Bad License",
                "collection": "prelinger",
                "licenseurl": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
            },
            {
                "identifier": "good-2",
                "title": "Good 2",
                "collection": "prelinger",
                "licenseurl": "",
            },
        ]
        d, cat = self._build_discoverer_and_catalog(tmp_path, docs)
        count = d.discover_and_catalog(cat, "ads")
        assert count == 2
        assert cat.get_item("good-1") is not None
        assert cat.get_item("bad-lic") is None
        assert cat.get_item("good-2") is not None
        cat.close()

    def test_enriches_before_saving(self, tmp_path):
        docs = [
            {
                "identifier": "enrich-save",
                "title": "Enrich Me",
                "collection": "prelinger",
                "licenseurl": "publicdomain",
            },
        ]
        meta = {
            "files": [{"name": "clip.mp4"}],
            "metadata": {"year": "1930", "description": "Enriched"},
        }
        d, cat = self._build_discoverer_and_catalog(tmp_path, docs, metadata_resp=meta)
        count = d.discover_and_catalog(cat, "ads")
        assert count == 1
        item = cat.get_item("enrich-save")
        assert "clip.mp4" in item.download_urls[0]
        cat.close()

    def test_empty_search_results(self, tmp_path):
        d, cat = self._build_discoverer_and_catalog(tmp_path, [])
        count = d.discover_and_catalog(cat, "ads")
        assert count == 0
        cat.close()

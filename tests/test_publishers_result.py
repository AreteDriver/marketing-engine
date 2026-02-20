"""Tests for marketing_engine.publishers.result."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from marketing_engine.enums import Platform
from marketing_engine.publishers.result import PublishResult


class TestPublishResultCreation:
    def test_minimal_fields(self):
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="post-123",
        )
        assert result.success is True
        assert result.platform == Platform.twitter
        assert result.post_id == "post-123"

    def test_all_fields(self):
        now = datetime.now(UTC)
        result = PublishResult(
            success=True,
            platform=Platform.linkedin,
            post_id="post-456",
            platform_post_id="li-789",
            post_url="https://linkedin.com/feed/update/li-789",
            error=None,
            published_at=now,
        )
        assert result.platform_post_id == "li-789"
        assert result.post_url == "https://linkedin.com/feed/update/li-789"
        assert result.published_at == now

    def test_failure_with_error(self):
        result = PublishResult(
            success=False,
            platform=Platform.reddit,
            post_id="post-err",
            error="API rate limit exceeded",
        )
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.platform_post_id is None
        assert result.post_url is None
        assert result.published_at is None


class TestPublishResultDefaults:
    def test_platform_post_id_defaults_none(self):
        result = PublishResult(success=True, platform=Platform.twitter, post_id="p1")
        assert result.platform_post_id is None

    def test_post_url_defaults_none(self):
        result = PublishResult(success=True, platform=Platform.twitter, post_id="p1")
        assert result.post_url is None

    def test_error_defaults_none(self):
        result = PublishResult(success=True, platform=Platform.twitter, post_id="p1")
        assert result.error is None

    def test_published_at_defaults_none(self):
        result = PublishResult(success=True, platform=Platform.twitter, post_id="p1")
        assert result.published_at is None


class TestPublishResultValidation:
    def test_missing_success_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(platform=Platform.twitter, post_id="p1")

    def test_missing_platform_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(success=True, post_id="p1")

    def test_missing_post_id_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(success=True, platform=Platform.twitter)

    def test_invalid_platform_raises(self):
        with pytest.raises(ValidationError):
            PublishResult(success=True, platform="instagram", post_id="p1")


class TestPublishResultSerialization:
    def test_roundtrip(self):
        now = datetime.now(UTC)
        original = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="p1",
            platform_post_id="tw-123",
            post_url="https://twitter.com/i/status/tw-123",
            published_at=now,
        )
        data = original.model_dump()
        restored = PublishResult(**data)
        assert restored.success == original.success
        assert restored.platform == original.platform
        assert restored.post_id == original.post_id
        assert restored.platform_post_id == original.platform_post_id
        assert restored.post_url == original.post_url
        assert restored.published_at == original.published_at

    def test_all_platforms_accepted(self):
        for plat in Platform:
            result = PublishResult(success=True, platform=plat, post_id="p1")
            assert result.platform == plat

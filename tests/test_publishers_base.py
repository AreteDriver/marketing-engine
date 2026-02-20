"""Tests for marketing_engine.publishers.base."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from marketing_engine.enums import ContentStream, Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.base import (
    DryRunPublisher,
    PlatformPublisher,
    get_publisher,
)
from marketing_engine.publishers.result import PublishResult


def _make_post(
    platform: Platform = Platform.twitter,
    content: str = "Test content",
    edited_content: str | None = None,
) -> PostDraft:
    return PostDraft(
        brief_id="brief-1",
        stream=ContentStream.project_marketing,
        platform=platform,
        content=content,
        edited_content=edited_content,
    )


# ---------------------------------------------------------------------------
# PlatformPublisher ABC
# ---------------------------------------------------------------------------


class TestPlatformPublisherABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            PlatformPublisher()

    def test_subclass_must_implement_publish(self):
        class Incomplete(PlatformPublisher):
            platform = Platform.twitter

            def validate_credentials(self) -> bool:
                return True

        with pytest.raises(TypeError):
            Incomplete()

    def test_subclass_must_implement_validate_credentials(self):
        class Incomplete(PlatformPublisher):
            platform = Platform.twitter

            def publish(self, post: PostDraft) -> PublishResult:
                return PublishResult(success=True, platform=self.platform, post_id=post.id)

        with pytest.raises(TypeError):
            Incomplete()


class TestEffectiveContent:
    def test_returns_content_when_no_edit(self):
        pub = DryRunPublisher()
        post = _make_post(content="original text")
        assert pub._effective_content(post) == "original text"

    def test_returns_edited_content_when_available(self):
        pub = DryRunPublisher()
        post = _make_post(content="original", edited_content="revised version")
        assert pub._effective_content(post) == "revised version"

    def test_returns_content_when_edited_is_empty_string(self):
        pub = DryRunPublisher()
        post = _make_post(content="original", edited_content="")
        assert pub._effective_content(post) == "original"


# ---------------------------------------------------------------------------
# DryRunPublisher
# ---------------------------------------------------------------------------


class TestDryRunPublisherInit:
    def test_default_platform_is_twitter(self):
        pub = DryRunPublisher()
        assert pub.platform == Platform.twitter

    def test_accepts_explicit_platform(self):
        pub = DryRunPublisher(platform=Platform.linkedin)
        assert pub.platform == Platform.linkedin

    def test_accepts_none_platform(self):
        pub = DryRunPublisher(platform=None)
        assert pub.platform == Platform.twitter


class TestDryRunPublisherPublish:
    def test_returns_publish_result(self):
        pub = DryRunPublisher()
        post = _make_post()
        result = pub.publish(post)
        assert isinstance(result, PublishResult)

    def test_result_is_success(self):
        pub = DryRunPublisher()
        result = pub.publish(_make_post())
        assert result.success is True

    def test_result_uses_post_platform(self):
        pub = DryRunPublisher(platform=Platform.twitter)
        post = _make_post(platform=Platform.linkedin)
        result = pub.publish(post)
        assert result.platform == Platform.linkedin

    def test_result_uses_post_id(self):
        pub = DryRunPublisher()
        post = _make_post()
        result = pub.publish(post)
        assert result.post_id == post.id

    def test_result_has_dry_run_id(self):
        pub = DryRunPublisher()
        result = pub.publish(_make_post())
        assert result.platform_post_id == "dry-run-id"

    def test_result_has_dry_run_url(self):
        pub = DryRunPublisher()
        result = pub.publish(_make_post())
        assert result.post_url == "https://example.com/dry-run"

    def test_result_has_published_at(self):
        pub = DryRunPublisher()
        result = pub.publish(_make_post())
        assert result.published_at is not None

    def test_result_has_no_error(self):
        pub = DryRunPublisher()
        result = pub.publish(_make_post())
        assert result.error is None


class TestDryRunPublisherValidateCredentials:
    def test_always_returns_true(self):
        pub = DryRunPublisher()
        assert pub.validate_credentials() is True

    def test_returns_true_for_all_platforms(self):
        for plat in Platform:
            pub = DryRunPublisher(platform=plat)
            assert pub.validate_credentials() is True


# ---------------------------------------------------------------------------
# get_publisher factory
# ---------------------------------------------------------------------------


class TestGetPublisherDryRun:
    def test_dry_run_returns_dry_run_publisher(self):
        pub = get_publisher(Platform.twitter, dry_run=True)
        assert isinstance(pub, DryRunPublisher)

    def test_dry_run_sets_platform(self):
        pub = get_publisher(Platform.linkedin, dry_run=True)
        assert pub.platform == Platform.linkedin

    def test_dry_run_works_for_unsupported_platforms(self):
        pub = get_publisher(Platform.youtube, dry_run=True)
        assert isinstance(pub, DryRunPublisher)
        assert pub.platform == Platform.youtube

    def test_dry_run_tiktok(self):
        pub = get_publisher(Platform.tiktok, dry_run=True)
        assert isinstance(pub, DryRunPublisher)
        assert pub.platform == Platform.tiktok


class TestGetPublisherReal:
    @patch("marketing_engine.publishers.twitter.get_platform_credentials", return_value={})
    def test_twitter_returns_twitter_publisher(self, _mock_creds):
        from marketing_engine.publishers.twitter import TwitterPublisher

        pub = get_publisher(Platform.twitter, dry_run=False)
        assert isinstance(pub, TwitterPublisher)

    @patch("marketing_engine.publishers.linkedin.get_platform_credentials", return_value={})
    def test_linkedin_returns_linkedin_publisher(self, _mock_creds):
        from marketing_engine.publishers.linkedin import LinkedInPublisher

        pub = get_publisher(Platform.linkedin, dry_run=False)
        assert isinstance(pub, LinkedInPublisher)

    @patch("marketing_engine.publishers.reddit.get_platform_credentials", return_value={})
    def test_reddit_returns_reddit_publisher(self, _mock_creds):
        from marketing_engine.publishers.reddit import RedditPublisher

        pub = get_publisher(Platform.reddit, dry_run=False)
        assert isinstance(pub, RedditPublisher)


class TestGetPublisherUnsupported:
    def test_youtube_raises_publish_error(self):
        with pytest.raises(PublishError, match="youtube"):
            get_publisher(Platform.youtube, dry_run=False)

    def test_tiktok_raises_publish_error(self):
        with pytest.raises(PublishError, match="tiktok"):
            get_publisher(Platform.tiktok, dry_run=False)

    def test_error_message_mentions_supported_platforms(self):
        with pytest.raises(PublishError, match="Supported"):
            get_publisher(Platform.youtube, dry_run=False)

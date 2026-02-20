"""Base publisher ABC and factory."""

from __future__ import annotations

import abc
from datetime import UTC, datetime

from marketing_engine.enums import Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.result import PublishResult


class PlatformPublisher(abc.ABC):
    """Abstract base for platform publishers."""

    platform: Platform

    @abc.abstractmethod
    def publish(self, post: PostDraft) -> PublishResult:
        """Publish a post and return the result."""

    @abc.abstractmethod
    def validate_credentials(self) -> bool:
        """Check that required credentials are configured."""

    def _effective_content(self, post: PostDraft) -> str:
        """Return edited content if available, else original."""
        return post.edited_content or post.content


class DryRunPublisher(PlatformPublisher):
    """Publisher that simulates success without making API calls."""

    def __init__(self, platform: Platform | None = None) -> None:
        self.platform = platform or Platform.twitter

    def publish(self, post: PostDraft) -> PublishResult:
        """Return a fake success result."""
        return PublishResult(
            success=True,
            platform=post.platform,
            post_id=post.id,
            platform_post_id="dry-run-id",
            post_url="https://example.com/dry-run",
            published_at=datetime.now(UTC),
        )

    def validate_credentials(self) -> bool:
        """Always valid for dry runs."""
        return True


def get_publisher(platform: Platform, dry_run: bool = False) -> PlatformPublisher:
    """Factory to get the appropriate publisher for a platform.

    Args:
        platform: Target platform.
        dry_run: If True, return a DryRunPublisher.

    Returns:
        A PlatformPublisher instance.

    Raises:
        PublishError: If the platform is not supported.
    """
    if dry_run:
        return DryRunPublisher(platform)

    from marketing_engine.publishers.linkedin import LinkedInPublisher
    from marketing_engine.publishers.reddit import RedditPublisher
    from marketing_engine.publishers.twitter import TwitterPublisher

    publishers: dict[Platform, type[PlatformPublisher]] = {
        Platform.twitter: TwitterPublisher,
        Platform.linkedin: LinkedInPublisher,
        Platform.reddit: RedditPublisher,
    }

    cls = publishers.get(platform)
    if cls is None:
        raise PublishError(
            f"No publisher available for platform: {platform}. "
            f"Supported: {', '.join(str(p) for p in publishers)}"
        )
    return cls()

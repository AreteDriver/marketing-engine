"""Twitter/X publisher using v2 API."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from marketing_engine.config import get_platform_credentials
from marketing_engine.enums import Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.base import PlatformPublisher
from marketing_engine.publishers.result import PublishResult

_TWEETS_URL = "https://api.twitter.com/2/tweets"


class TwitterPublisher(PlatformPublisher):
    """Publish posts to Twitter/X via the v2 API."""

    platform = Platform.twitter

    def __init__(self) -> None:
        self._creds = get_platform_credentials("twitter")

    def validate_credentials(self) -> bool:
        """Check that the bearer token is set."""
        return bool(self._creds.get("bearer_token"))

    def publish(self, post: PostDraft) -> PublishResult:
        """Post a tweet via the Twitter v2 API."""
        if not self.validate_credentials():
            return PublishResult(
                success=False,
                platform=self.platform,
                post_id=post.id,
                error="Missing MKEN_TWITTER_BEARER_TOKEN",
            )

        content = self._effective_content(post)
        headers = {
            "Authorization": f"Bearer {self._creds['bearer_token']}",
            "Content-Type": "application/json",
        }
        payload = {"text": content}

        try:
            resp = httpx.post(_TWEETS_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            tweet_id = data.get("id", "")
            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=post.id,
                platform_post_id=tweet_id,
                post_url=f"https://twitter.com/i/status/{tweet_id}" if tweet_id else None,
                published_at=datetime.now(UTC),
            )
        except httpx.HTTPStatusError as exc:
            raise PublishError(
                f"Twitter API error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise PublishError(f"Twitter request failed: {exc}") from exc

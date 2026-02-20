"""LinkedIn publisher using v2 UGC Posts API."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from marketing_engine.config import get_platform_credentials
from marketing_engine.enums import Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.base import PlatformPublisher
from marketing_engine.publishers.result import PublishResult

_UGC_POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"


class LinkedInPublisher(PlatformPublisher):
    """Publish posts to LinkedIn via the UGC Posts API."""

    platform = Platform.linkedin

    def __init__(self) -> None:
        self._creds = get_platform_credentials("linkedin")

    def validate_credentials(self) -> bool:
        """Check that access token and person ID are set."""
        return bool(self._creds.get("access_token") and self._creds.get("person_id"))

    def publish(self, post: PostDraft) -> PublishResult:
        """Create a LinkedIn UGC post."""
        if not self.validate_credentials():
            return PublishResult(
                success=False,
                platform=self.platform,
                post_id=post.id,
                error="Missing MKEN_LINKEDIN_ACCESS_TOKEN or MKEN_LINKEDIN_PERSON_ID",
            )

        content = self._effective_content(post)
        person_id = self._creds["person_id"]
        headers = {
            "Authorization": f"Bearer {self._creds['access_token']}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        payload = {
            "author": f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        try:
            resp = httpx.post(_UGC_POSTS_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            post_urn = resp.headers.get("x-restli-id", "")
            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=post.id,
                platform_post_id=post_urn,
                post_url=f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else None,
                published_at=datetime.now(UTC),
            )
        except httpx.HTTPStatusError as exc:
            raise PublishError(
                f"LinkedIn API error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise PublishError(f"LinkedIn request failed: {exc}") from exc

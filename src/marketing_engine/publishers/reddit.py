"""Reddit publisher using OAuth2 API."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from marketing_engine.config import get_platform_credentials
from marketing_engine.enums import Platform
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.base import PlatformPublisher
from marketing_engine.publishers.result import PublishResult

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_SUBMIT_URL = "https://oauth.reddit.com/api/submit"
_USER_AGENT = "marketing-engine/0.1.0"


class RedditPublisher(PlatformPublisher):
    """Publish posts to Reddit via the OAuth2 API."""

    platform = Platform.reddit

    def __init__(self) -> None:
        self._creds = get_platform_credentials("reddit")

    def validate_credentials(self) -> bool:
        """Check that all required Reddit credentials are set."""
        required = ["client_id", "client_secret", "username", "password"]
        return all(self._creds.get(k) for k in required)

    def _get_access_token(self) -> str:
        """Obtain an OAuth2 access token via password grant."""
        auth = (self._creds["client_id"], self._creds["client_secret"])
        data = {
            "grant_type": "password",
            "username": self._creds["username"],
            "password": self._creds["password"],
        }
        headers = {"User-Agent": _USER_AGENT}

        try:
            resp = httpx.post(_TOKEN_URL, auth=auth, data=data, headers=headers, timeout=30)
            resp.raise_for_status()
            token = resp.json().get("access_token", "")
            if not token:
                raise PublishError("Reddit OAuth returned empty access token")
            return token
        except httpx.HTTPError as exc:
            raise PublishError(f"Reddit OAuth failed: {exc}") from exc

    def publish(self, post: PostDraft) -> PublishResult:
        """Submit a self-post to a subreddit."""
        if not self.validate_credentials():
            return PublishResult(
                success=False,
                platform=self.platform,
                post_id=post.id,
                error="Missing Reddit credentials (MKEN_REDDIT_*)",
            )

        subreddit = post.subreddit
        if not subreddit:
            return PublishResult(
                success=False,
                platform=self.platform,
                post_id=post.id,
                error="No subreddit specified on post",
            )

        content = self._effective_content(post)
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": _USER_AGENT,
        }
        # Use first line as title, rest as body
        lines = content.strip().split("\n", 1)
        title = lines[0][:300]  # Reddit title limit
        body = lines[1].strip() if len(lines) > 1 else ""

        data = {
            "kind": "self",
            "sr": subreddit,
            "title": title,
            "text": body,
        }

        try:
            resp = httpx.post(_SUBMIT_URL, data=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result_data = resp.json()
            # Reddit returns nested jQuery-style response
            post_url = None
            post_id_reddit = None
            if "json" in result_data and "data" in result_data["json"]:
                post_url = result_data["json"]["data"].get("url")
                post_id_reddit = result_data["json"]["data"].get("id")

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=post.id,
                platform_post_id=post_id_reddit,
                post_url=post_url,
                published_at=datetime.now(UTC),
            )
        except httpx.HTTPStatusError as exc:
            raise PublishError(
                f"Reddit API error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise PublishError(f"Reddit request failed: {exc}") from exc

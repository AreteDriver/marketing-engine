"""Format agent for adapting posts to platform-specific constraints."""

from __future__ import annotations

import json
from typing import Any

from marketing_engine.agents.base import BaseAgent
from marketing_engine.enums import ContentStream, Platform

_DEFAULT_PLATFORM_LIMITS = {
    "twitter": {"max_chars": 280, "max_hashtags": 3},
    "linkedin": {"max_chars": 3000, "max_hashtags": 5},
    "reddit": {"max_chars": 10000, "max_hashtags": 0},
    "youtube": {"max_chars": 5000, "max_hashtags": 15},
    "tiktok": {"max_chars": 2200, "max_hashtags": 5},
}


class FormatAgent(BaseAgent):
    """Reformats post content for specific platform constraints."""

    def __init__(self, llm: Any, config: dict) -> None:
        super().__init__(llm, config)
        self._platform_rules = config.get("platform_rules", {})
        self._current_platform: Platform = Platform.twitter

    @property
    def system_prompt(self) -> str:
        platform_name = self._current_platform.value
        rules = self._platform_rules.get(platform_name, {})
        limits = _DEFAULT_PLATFORM_LIMITS.get(platform_name, {})
        max_chars = rules.get("max_chars", limits.get("max_chars", 280))
        max_hashtags = rules.get("max_hashtags", limits.get("max_hashtags", 3))

        subreddit_note = ""
        if self._current_platform == Platform.reddit:
            subreddit_note = (
                ' Include "subreddit" key with the target subreddit name (without r/ prefix).'
            )

        return (
            f"You are a social media formatter. "
            f"Reformat the given post for {platform_name}. "
            f"Maximum {max_chars} characters. "
            f"Maximum {max_hashtags} hashtags. "
            f"Respect the platform's conventions and culture.{subreddit_note} "
            f'Output ONLY JSON: {{"content": "...", "hashtags": [...], '
            f'"subreddit": "..." (reddit only, null otherwise)}}'
        )

    def build_user_prompt(
        self,
        content: str = "",
        platform: Platform | None = None,
        stream: ContentStream | None = None,
        **kwargs: Any,
    ) -> str:
        """Build prompt with content and platform context."""
        if platform is not None:
            self._current_platform = platform

        platform_name = self._current_platform.value
        stream_name = stream.value if stream else "general"
        rules = self._platform_rules.get(platform_name, {})
        style_notes = rules.get("style_notes", "")

        lines = [
            f"Reformat this post for {platform_name}:",
            "",
            content,
            "",
            f"Content stream: {stream_name}",
        ]
        if style_notes:
            lines.append(f"Platform style notes: {style_notes}")

        return "\n".join(lines)

    def parse_response(self, raw: str) -> dict:
        """Parse JSON response into formatted post data."""
        data = json.loads(raw)
        return {
            "content": data.get("content", ""),
            "hashtags": data.get("hashtags", []),
            "subreddit": data.get("subreddit"),
        }

    def _enforce_limits(self, result: dict, platform: Platform) -> dict:
        """Enforce platform character and hashtag limits.

        Truncates content at word boundary and caps hashtag count.
        """
        rules = self._platform_rules.get(platform.value, {})
        defaults = _DEFAULT_PLATFORM_LIMITS.get(platform.value, {})
        max_chars = rules.get("max_chars", defaults.get("max_chars", 280))
        max_hashtags = rules.get("max_hashtags", defaults.get("max_hashtags", 3))

        content = result.get("content", "")
        if len(content) > max_chars:
            # Truncate at word boundary
            truncated = content[:max_chars]
            last_space = truncated.rfind(" ")
            if last_space > max_chars // 2:
                truncated = truncated[:last_space]
            # Add ellipsis if we truncated
            if len(truncated) + 3 <= max_chars:
                truncated += "..."
            result["content"] = truncated

        hashtags = result.get("hashtags", [])
        if len(hashtags) > max_hashtags:
            result["hashtags"] = hashtags[:max_hashtags]

        # Strip subreddit for non-reddit platforms
        if platform != Platform.reddit:
            result["subreddit"] = None

        return result

    def run(
        self,
        content: str = "",
        platform: Platform | None = None,
        stream: ContentStream | None = None,
        **kwargs: Any,
    ) -> dict:
        """Format content for a specific platform with limit enforcement."""
        if platform is not None:
            self._current_platform = platform
        raw_result = super().run(content=content, platform=platform, stream=stream)
        return self._enforce_limits(raw_result, self._current_platform)

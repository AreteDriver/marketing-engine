"""Queue agent for deterministic post scheduling."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from marketing_engine.models import PostDraft

_DEFAULT_POSTING_DAYS = [1, 2, 3, 4, 5, 6]  # Tuesday through Sunday (0=Mon)

_DEFAULT_WINDOWS = {
    "twitter": [
        {"hour": 9, "minute": 0},
        {"hour": 12, "minute": 30},
        {"hour": 17, "minute": 0},
    ],
    "linkedin": [
        {"hour": 8, "minute": 0},
        {"hour": 12, "minute": 0},
        {"hour": 17, "minute": 30},
    ],
    "reddit": [
        {"hour": 10, "minute": 0},
        {"hour": 14, "minute": 0},
        {"hour": 19, "minute": 0},
    ],
    "youtube": [
        {"hour": 10, "minute": 0},
        {"hour": 15, "minute": 0},
    ],
    "tiktok": [
        {"hour": 11, "minute": 0},
        {"hour": 19, "minute": 0},
        {"hour": 21, "minute": 0},
    ],
}


class QueueAgent:
    """Deterministic post scheduler — no LLM needed.

    Distributes posts across the week using round-robin allocation,
    respecting per-platform posting windows and avoiding adjacent
    same-stream posts.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        tz_name = config.get("timezone", "America/New_York")
        self._tz = ZoneInfo(tz_name)

    def _get_posting_days(self) -> list[int]:
        """Return configured posting days as weekday offsets (0=Monday)."""
        return self.config.get("posting_days", _DEFAULT_POSTING_DAYS)

    def _get_windows(self, platform: str) -> list[dict]:
        """Return posting time windows for a platform."""
        windows_cfg = self.config.get("posting_windows", {})
        return windows_cfg.get(
            platform,
            _DEFAULT_WINDOWS.get(
                platform,
                [
                    {"hour": 10, "minute": 0},
                    {"hour": 15, "minute": 0},
                ],
            ),
        )

    def _resolve_day(self, week_of: date, day_offset: int) -> date:
        """Resolve a weekday offset to an actual date within the week.

        Args:
            week_of: The Monday of the target week.
            day_offset: Weekday offset (0=Monday, 6=Sunday).

        Returns:
            The resolved date.
        """
        return week_of + timedelta(days=day_offset)

    def schedule(self, posts: list[PostDraft], week_of: date) -> list[PostDraft]:
        """Assign scheduled_time to each post.

        Algorithm:
        1. Group posts by platform.
        2. For each platform, distribute across posting days via round-robin.
        3. Assign specific times from the platform's posting windows.
        4. Swap adjacent same-stream posts to add variety.

        Args:
            posts: List of PostDraft objects to schedule.
            week_of: The Monday of the target week.

        Returns:
            The same list with scheduled_time set on each post.
        """
        if not posts:
            return posts

        posting_days = self._get_posting_days()
        if not posting_days:
            posting_days = _DEFAULT_POSTING_DAYS

        # Group posts by platform
        by_platform: dict[str, list[PostDraft]] = {}
        for post in posts:
            platform_key = post.platform.value
            if platform_key not in by_platform:
                by_platform[platform_key] = []
            by_platform[platform_key].append(post)

        # Schedule each platform group
        for platform_key, platform_posts in by_platform.items():
            windows = self._get_windows(platform_key)
            if not windows:
                windows = [{"hour": 10, "minute": 0}]

            day_idx = 0

            for window_idx, post in enumerate(platform_posts):
                # Pick the day
                day_offset = posting_days[day_idx % len(posting_days)]
                post_date = self._resolve_day(week_of, day_offset)

                # Pick the time window
                window = windows[window_idx % len(windows)]
                post_time = time(
                    hour=window.get("hour", 10),
                    minute=window.get("minute", 0),
                )

                # Combine date + time + timezone
                naive_dt = datetime.combine(post_date, post_time)
                aware_dt = naive_dt.replace(tzinfo=self._tz)
                post.scheduled_time = aware_dt

                # Advance day after cycling through all windows
                if (window_idx + 1) % len(windows) == 0:
                    day_idx += 1

        # Swap adjacent same-stream posts
        self._dedup_adjacent(posts)

        return posts

    def _dedup_adjacent(self, posts: list[PostDraft]) -> None:
        """Swap adjacent posts if they belong to the same content stream.

        Sorts by scheduled_time first, then checks neighbors. When two
        adjacent posts share a stream, the second one is swapped with the
        next different-stream post (if any).
        """
        # Sort by scheduled time for adjacency check
        scheduled = [p for p in posts if p.scheduled_time is not None]
        scheduled.sort(key=lambda p: p.scheduled_time)  # type: ignore[arg-type]

        for i in range(len(scheduled) - 1):
            if scheduled[i].stream == scheduled[i + 1].stream:
                # Find next post with a different stream to swap
                for j in range(i + 2, len(scheduled)):
                    if scheduled[j].stream != scheduled[i].stream:
                        # Swap scheduled times
                        scheduled[i + 1].scheduled_time, scheduled[j].scheduled_time = (
                            scheduled[j].scheduled_time,
                            scheduled[i + 1].scheduled_time,
                        )
                        # Re-sort for subsequent adjacency checks
                        scheduled.sort(key=lambda p: p.scheduled_time)  # type: ignore[arg-type]
                        break

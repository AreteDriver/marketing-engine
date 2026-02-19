"""Tests for the QueueAgent deterministic post scheduler."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from marketing_engine.agents.queue import _DEFAULT_POSTING_DAYS, _DEFAULT_WINDOWS, QueueAgent
from marketing_engine.enums import ContentStream, Platform
from marketing_engine.models import PostDraft

# Fixed Monday for deterministic tests
WEEK_OF = date(2025, 3, 3)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post(
    platform: Platform = Platform.twitter,
    stream: ContentStream = ContentStream.project_marketing,
    brief_id: str = "brief-1",
    content: str = "Test content",
) -> PostDraft:
    """Create a PostDraft for testing."""
    return PostDraft(
        brief_id=brief_id,
        stream=stream,
        platform=platform,
        content=content,
    )


# ---------------------------------------------------------------------------
# schedule() basics
# ---------------------------------------------------------------------------


class TestScheduleBasics:
    """Basic schedule() behavior tests."""

    def test_empty_list_returns_empty(self) -> None:
        agent = QueueAgent(config={})
        result = agent.schedule([], WEEK_OF)
        assert result == []

    def test_assigns_scheduled_time_to_all_posts(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [_post(), _post(platform=Platform.linkedin)]
        agent.schedule(posts, WEEK_OF)
        for p in posts:
            assert p.scheduled_time is not None

    def test_all_scheduled_times_have_timezone(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [_post(), _post(platform=Platform.linkedin)]
        agent.schedule(posts, WEEK_OF)
        for p in posts:
            assert p.scheduled_time is not None
            assert p.scheduled_time.tzinfo is not None


# ---------------------------------------------------------------------------
# Timezone handling
# ---------------------------------------------------------------------------


class TestTimezones:
    """Tests for timezone configuration."""

    def test_utc_timezone(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [_post()]
        agent.schedule(posts, WEEK_OF)
        assert posts[0].scheduled_time is not None
        assert posts[0].scheduled_time.tzinfo == ZoneInfo("UTC")

    def test_new_york_timezone(self) -> None:
        agent = QueueAgent(config={"timezone": "America/New_York"})
        posts = [_post()]
        agent.schedule(posts, WEEK_OF)
        assert posts[0].scheduled_time is not None
        assert posts[0].scheduled_time.tzinfo == ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Posting days
# ---------------------------------------------------------------------------


class TestPostingDays:
    """Tests for posting day distribution."""

    def test_distributes_across_posting_days(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        # 6 twitter posts should cycle through posting days
        posts = [_post() for _ in range(6)]
        agent.schedule(posts, WEEK_OF)
        dates_used = {p.scheduled_time.date() for p in posts if p.scheduled_time}
        # With 3 windows and 6 posts, at least 2 distinct dates should be used
        assert len(dates_used) >= 2

    def test_default_posting_days_are_tue_through_sun(self) -> None:
        assert _DEFAULT_POSTING_DAYS == [1, 2, 3, 4, 5, 6]

    def test_custom_posting_days(self) -> None:
        # Only schedule on Wednesday (2) and Friday (4)
        agent = QueueAgent(config={"timezone": "UTC", "posting_days": [2, 4]})
        posts = [_post() for _ in range(4)]
        agent.schedule(posts, WEEK_OF)
        for p in posts:
            assert p.scheduled_time is not None
            weekday = p.scheduled_time.date().weekday()
            assert weekday in (2, 4), f"Expected Wed or Fri, got weekday={weekday}"


# ---------------------------------------------------------------------------
# Posting windows
# ---------------------------------------------------------------------------


class TestPostingWindows:
    """Tests for time window allocation."""

    def test_single_twitter_post_gets_first_window(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [_post()]
        agent.schedule(posts, WEEK_OF)
        assert posts[0].scheduled_time is not None
        first_window = _DEFAULT_WINDOWS["twitter"][0]
        assert posts[0].scheduled_time.hour == first_window["hour"]
        assert posts[0].scheduled_time.minute == first_window["minute"]

    def test_cycles_through_time_windows(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [_post() for _ in range(3)]
        agent.schedule(posts, WEEK_OF)
        hours = [p.scheduled_time.hour for p in posts if p.scheduled_time]
        expected_hours = [w["hour"] for w in _DEFAULT_WINDOWS["twitter"]]
        assert hours == expected_hours

    def test_custom_posting_windows(self) -> None:
        custom_windows = {"twitter": [{"hour": 6, "minute": 30}]}
        agent = QueueAgent(config={"timezone": "UTC", "posting_windows": custom_windows})
        posts = [_post()]
        agent.schedule(posts, WEEK_OF)
        assert posts[0].scheduled_time is not None
        assert posts[0].scheduled_time.hour == 6
        assert posts[0].scheduled_time.minute == 30


# ---------------------------------------------------------------------------
# Platform grouping
# ---------------------------------------------------------------------------


class TestPlatformGrouping:
    """Tests for per-platform scheduling."""

    def test_multiple_platforms_grouped_correctly(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        posts = [
            _post(platform=Platform.twitter),
            _post(platform=Platform.linkedin),
            _post(platform=Platform.twitter),
        ]
        agent.schedule(posts, WEEK_OF)
        # Each platform gets its own windows
        twitter_posts = [p for p in posts if p.platform == Platform.twitter]
        linkedin_posts = [p for p in posts if p.platform == Platform.linkedin]
        # Twitter first post should get twitter's first window
        assert twitter_posts[0].scheduled_time is not None
        assert twitter_posts[0].scheduled_time.hour == _DEFAULT_WINDOWS["twitter"][0]["hour"]
        # LinkedIn post should get linkedin's first window
        assert linkedin_posts[0].scheduled_time is not None
        assert linkedin_posts[0].scheduled_time.hour == _DEFAULT_WINDOWS["linkedin"][0]["hour"]


# ---------------------------------------------------------------------------
# _dedup_adjacent
# ---------------------------------------------------------------------------


class TestDedupAdjacent:
    """Tests for adjacent same-stream deduplication."""

    def test_swaps_adjacent_same_stream_posts(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        tz = ZoneInfo("UTC")
        p1 = _post(stream=ContentStream.project_marketing)
        p2 = _post(stream=ContentStream.project_marketing)
        p3 = _post(stream=ContentStream.benchgoblins)
        # Assign adjacent times to same-stream posts
        base = datetime(2025, 3, 4, 9, 0, tzinfo=tz)
        p1.scheduled_time = base
        p2.scheduled_time = base + timedelta(hours=1)
        p3.scheduled_time = base + timedelta(hours=2)

        agent._dedup_adjacent([p1, p2, p3])

        # After dedup, p2 and p3 should be swapped (p3 was different stream)
        sorted_posts = sorted([p1, p2, p3], key=lambda p: p.scheduled_time)
        # The middle post should now be benchgoblins (different stream from first)
        assert sorted_posts[0].stream != sorted_posts[1].stream

    def test_leaves_different_stream_adjacent_alone(self) -> None:
        agent = QueueAgent(config={"timezone": "UTC"})
        tz = ZoneInfo("UTC")
        p1 = _post(stream=ContentStream.project_marketing)
        p2 = _post(stream=ContentStream.benchgoblins)
        base = datetime(2025, 3, 4, 9, 0, tzinfo=tz)
        p1.scheduled_time = base
        p2.scheduled_time = base + timedelta(hours=1)
        original_t1 = p1.scheduled_time
        original_t2 = p2.scheduled_time

        agent._dedup_adjacent([p1, p2])

        assert p1.scheduled_time == original_t1
        assert p2.scheduled_time == original_t2


# ---------------------------------------------------------------------------
# _resolve_day
# ---------------------------------------------------------------------------


class TestResolveDay:
    """Tests for _resolve_day()."""

    def test_returns_correct_date_offset(self) -> None:
        agent = QueueAgent(config={})
        # WEEK_OF is Monday 2025-03-03, offset 1 = Tuesday 2025-03-04
        resolved = agent._resolve_day(WEEK_OF, 1)
        assert resolved == date(2025, 3, 4)
        assert resolved.weekday() == 1  # Tuesday

    def test_offset_zero_returns_monday(self) -> None:
        agent = QueueAgent(config={})
        resolved = agent._resolve_day(WEEK_OF, 0)
        assert resolved == WEEK_OF

    def test_offset_six_returns_sunday(self) -> None:
        agent = QueueAgent(config={})
        resolved = agent._resolve_day(WEEK_OF, 6)
        assert resolved == date(2025, 3, 9)
        assert resolved.weekday() == 6  # Sunday

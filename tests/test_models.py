"""Tests for marketing_engine.models."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform
from marketing_engine.models import ContentBrief, PipelineRun, PostDraft, WeeklyQueue


class TestContentBrief:
    def test_default_id_is_uuid(self):
        brief = ContentBrief(
            topic="t",
            angle="a",
            target_audience="devs",
            stream=ContentStream.project_marketing,
            platforms=[Platform.twitter],
        )
        UUID(brief.id)

    def test_default_created_at_is_utc(self):
        brief = ContentBrief(
            topic="t",
            angle="a",
            target_audience="devs",
            stream=ContentStream.project_marketing,
            platforms=[Platform.twitter],
        )
        assert brief.created_at.tzinfo is not None
        before = datetime.now(UTC)
        assert brief.created_at <= before

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ContentBrief()

    def test_relevant_links_defaults_empty(self):
        brief = ContentBrief(
            topic="t",
            angle="a",
            target_audience="devs",
            stream=ContentStream.project_marketing,
            platforms=[Platform.twitter],
        )
        assert brief.relevant_links == []

    def test_serialization_roundtrip(self, sample_brief):
        data = sample_brief.model_dump()
        restored = ContentBrief(**data)
        assert restored.id == sample_brief.id
        assert restored.topic == sample_brief.topic
        assert restored.stream == sample_brief.stream
        assert restored.platforms == sample_brief.platforms

    def test_bad_stream_raises(self):
        with pytest.raises(ValidationError):
            ContentBrief(
                topic="t",
                angle="a",
                target_audience="devs",
                stream="nonexistent_stream",
                platforms=[Platform.twitter],
            )

    def test_bad_platform_raises(self):
        with pytest.raises(ValidationError):
            ContentBrief(
                topic="t",
                angle="a",
                target_audience="devs",
                stream=ContentStream.project_marketing,
                platforms=["fakebook"],
            )

    def test_relevant_links_stored(self):
        brief = ContentBrief(
            topic="t",
            angle="a",
            target_audience="devs",
            stream=ContentStream.project_marketing,
            platforms=[Platform.twitter],
            relevant_links=["https://example.com"],
        )
        assert brief.relevant_links == ["https://example.com"]


class TestPostDraft:
    def test_default_id_is_uuid(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        UUID(draft.id)

    def test_default_approval_pending(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        assert draft.approval_status == ApprovalStatus.pending

    def test_default_lists_empty(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        assert draft.media_urls == []
        assert draft.hashtags == []

    def test_default_cta_empty_string(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        assert draft.cta_url == ""

    def test_optional_fields_none_by_default(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        assert draft.scheduled_time is None
        assert draft.edited_content is None
        assert draft.rejection_reason is None
        assert draft.subreddit is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PostDraft()

    def test_timestamps_are_utc(self):
        draft = PostDraft(
            brief_id="abc",
            stream=ContentStream.eve_content,
            platform=Platform.reddit,
            content="Hello world",
        )
        assert draft.created_at.tzinfo is not None
        assert draft.updated_at.tzinfo is not None

    def test_serialization_roundtrip(self, sample_post):
        data = sample_post.model_dump()
        restored = PostDraft(**data)
        assert restored.id == sample_post.id
        assert restored.content == sample_post.content
        assert restored.platform == sample_post.platform
        assert restored.approval_status == sample_post.approval_status

    def test_scheduled_time_preserved(self, sample_post):
        assert sample_post.scheduled_time is not None
        assert sample_post.scheduled_time.tzinfo is not None


class TestPipelineRun:
    def test_default_status_running(self):
        run = PipelineRun(week_of=date(2025, 3, 3))
        assert run.status == "running"

    def test_default_counts_zero(self):
        run = PipelineRun(week_of=date(2025, 3, 3))
        assert run.briefs_count == 0
        assert run.drafts_count == 0
        assert run.posts_count == 0

    def test_default_optional_fields_none(self):
        run = PipelineRun(week_of=date(2025, 3, 3))
        assert run.completed_at is None
        assert run.error is None

    def test_required_week_of(self):
        with pytest.raises(ValidationError):
            PipelineRun()

    def test_id_is_uuid(self, sample_pipeline_run):
        UUID(sample_pipeline_run.id)

    def test_serialization_roundtrip(self, sample_pipeline_run):
        data = sample_pipeline_run.model_dump()
        restored = PipelineRun(**data)
        assert restored.week_of == sample_pipeline_run.week_of
        assert restored.status == sample_pipeline_run.status


class TestWeeklyQueue:
    def test_empty_queue_totals(self):
        queue = WeeklyQueue(week_of=date(2025, 3, 3))
        assert queue.total_by_platform() == {}
        assert queue.total_by_stream() == {}
        assert queue.pending_count() == 0
        assert queue.approved_count() == 0

    def test_total_by_platform(self):
        posts = [
            PostDraft(
                brief_id="b1",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="tweet",
            ),
            PostDraft(
                brief_id="b2",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="tweet 2",
            ),
            PostDraft(
                brief_id="b3",
                stream=ContentStream.eve_content,
                platform=Platform.linkedin,
                content="post",
            ),
        ]
        queue = WeeklyQueue(week_of=date(2025, 3, 3), posts=posts)
        by_platform = queue.total_by_platform()
        assert by_platform[Platform.twitter] == 2
        assert by_platform[Platform.linkedin] == 1

    def test_total_by_stream(self):
        posts = [
            PostDraft(
                brief_id="b1",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="tweet",
            ),
            PostDraft(
                brief_id="b2",
                stream=ContentStream.eve_content,
                platform=Platform.reddit,
                content="post",
            ),
            PostDraft(
                brief_id="b3",
                stream=ContentStream.eve_content,
                platform=Platform.linkedin,
                content="post 2",
            ),
        ]
        queue = WeeklyQueue(week_of=date(2025, 3, 3), posts=posts)
        by_stream = queue.total_by_stream()
        assert by_stream[ContentStream.project_marketing] == 1
        assert by_stream[ContentStream.eve_content] == 2

    def test_pending_count(self):
        posts = [
            PostDraft(
                brief_id="b1",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.pending,
            ),
            PostDraft(
                brief_id="b2",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.approved,
            ),
            PostDraft(
                brief_id="b3",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.pending,
            ),
        ]
        queue = WeeklyQueue(week_of=date(2025, 3, 3), posts=posts)
        assert queue.pending_count() == 2

    def test_approved_count_includes_edited(self):
        posts = [
            PostDraft(
                brief_id="b1",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.approved,
            ),
            PostDraft(
                brief_id="b2",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.edited,
            ),
            PostDraft(
                brief_id="b3",
                stream=ContentStream.project_marketing,
                platform=Platform.twitter,
                content="t",
                approval_status=ApprovalStatus.rejected,
            ),
        ]
        queue = WeeklyQueue(week_of=date(2025, 3, 3), posts=posts)
        assert queue.approved_count() == 2

    def test_id_is_uuid(self):
        queue = WeeklyQueue(week_of=date(2025, 3, 3))
        UUID(queue.id)

"""Tests for DB publish methods."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform, PublishStatus
from marketing_engine.models import PostDraft
from marketing_engine.publishers.result import PublishResult


def _make_post(
    brief_id: str,
    post_id: str = "pub-post-1",
    platform: Platform = Platform.twitter,
    approval_status: ApprovalStatus = ApprovalStatus.approved,
    publish_status: PublishStatus = PublishStatus.pending,
    scheduled_time: datetime | None = None,
) -> PostDraft:
    return PostDraft(
        id=post_id,
        brief_id=brief_id,
        stream=ContentStream.project_marketing,
        platform=platform,
        content=f"Post {post_id}",
        approval_status=approval_status,
        publish_status=publish_status,
        scheduled_time=scheduled_time or datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        created_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
        updated_at=datetime(2025, 3, 3, 12, 0, tzinfo=UTC),
    )


@pytest.fixture()
def _db_setup(tmp_db, sample_brief, sample_pipeline_run):
    """Insert pipeline run and brief so foreign keys are satisfied."""
    tmp_db.save_pipeline_run(sample_pipeline_run)
    tmp_db.save_brief(sample_brief, sample_pipeline_run.id)
    return tmp_db, sample_brief, sample_pipeline_run


# ---------------------------------------------------------------------------
# get_publishable
# ---------------------------------------------------------------------------


class TestGetPublishable:
    def test_returns_approved_pending_publish(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            approval_status=ApprovalStatus.approved,
            publish_status=PublishStatus.pending,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert len(result) == 1
        assert result[0].id == post.id

    def test_returns_edited_pending_publish(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="edited-1",
            approval_status=ApprovalStatus.edited,
            publish_status=PublishStatus.pending,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert len(result) == 1
        assert result[0].id == "edited-1"

    def test_excludes_pending_approval(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="unapproved",
            approval_status=ApprovalStatus.pending,
            publish_status=PublishStatus.pending,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []

    def test_excludes_rejected(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="rejected-1",
            approval_status=ApprovalStatus.rejected,
            publish_status=PublishStatus.pending,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []

    def test_excludes_already_published(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="already-pub",
            approval_status=ApprovalStatus.approved,
            publish_status=PublishStatus.published,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []

    def test_excludes_failed_publish(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="failed-pub",
            approval_status=ApprovalStatus.approved,
            publish_status=PublishStatus.failed,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []

    def test_excludes_future_scheduled(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(
            brief.id,
            post_id="future-1",
            approval_status=ApprovalStatus.approved,
            publish_status=PublishStatus.pending,
            scheduled_time=datetime(2025, 3, 5, 10, 0, tzinfo=UTC),
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []

    def test_includes_exactly_at_now(self, _db_setup):
        db, brief, run = _db_setup
        exact_time = datetime(2025, 3, 4, 14, 0, tzinfo=UTC)
        post = _make_post(
            brief.id,
            post_id="exact-time",
            approval_status=ApprovalStatus.approved,
            publish_status=PublishStatus.pending,
            scheduled_time=exact_time,
        )
        db.save_draft(post, run.id)

        result = db.get_publishable(exact_time)

        assert len(result) == 1

    def test_returns_sorted_by_scheduled_time(self, _db_setup):
        db, brief, run = _db_setup
        post_late = _make_post(
            brief.id,
            post_id="late",
            scheduled_time=datetime(2025, 3, 4, 16, 0, tzinfo=UTC),
        )
        post_early = _make_post(
            brief.id,
            post_id="early",
            scheduled_time=datetime(2025, 3, 4, 8, 0, tzinfo=UTC),
        )
        db.save_draft(post_late, run.id)
        db.save_draft(post_early, run.id)

        result = db.get_publishable(datetime(2025, 3, 4, 18, 0, tzinfo=UTC))

        assert len(result) == 2
        assert result[0].id == "early"
        assert result[1].id == "late"

    def test_empty_table_returns_empty(self, _db_setup):
        db, _, _ = _db_setup

        result = db.get_publishable(datetime(2025, 3, 4, 12, 0, tzinfo=UTC))

        assert result == []


# ---------------------------------------------------------------------------
# update_publish_status
# ---------------------------------------------------------------------------


class TestUpdatePublishStatus:
    def test_sets_published_status(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id)
        db.save_draft(post, run.id)

        db.update_publish_status(post.id, PublishStatus.published)

        updated = db.get_post(post.id)
        assert updated.publish_status == PublishStatus.published

    def test_sets_failed_status(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="fail-status")
        db.save_draft(post, run.id)

        db.update_publish_status(post.id, PublishStatus.failed)

        updated = db.get_post(post.id)
        assert updated.publish_status == PublishStatus.failed

    def test_sets_published_at(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="pub-at")
        db.save_draft(post, run.id)
        pub_time = datetime(2025, 3, 4, 14, 30, tzinfo=UTC)

        db.update_publish_status(post.id, PublishStatus.published, published_at=pub_time)

        updated = db.get_post(post.id)
        assert updated.published_at is not None
        assert updated.published_at.replace(tzinfo=UTC) == pub_time

    def test_sets_post_url(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="url-test")
        db.save_draft(post, run.id)

        db.update_publish_status(
            post.id, PublishStatus.published, post_url="https://twitter.com/post/123"
        )

        updated = db.get_post(post.id)
        assert updated.post_url == "https://twitter.com/post/123"

    def test_sets_platform_post_id(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="plat-id")
        db.save_draft(post, run.id)

        db.update_publish_status(post.id, PublishStatus.published, platform_post_id="tweet-456")

        updated = db.get_post(post.id)
        assert updated.platform_post_id == "tweet-456"

    def test_sets_publish_error(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="err-test")
        db.save_draft(post, run.id)

        db.update_publish_status(post.id, PublishStatus.failed, publish_error="Rate limit exceeded")

        updated = db.get_post(post.id)
        assert updated.publish_error == "Rate limit exceeded"

    def test_updates_updated_at(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="ts-test")
        db.save_draft(post, run.id)
        original = db.get_post(post.id)

        db.update_publish_status(post.id, PublishStatus.published)

        updated = db.get_post(post.id)
        assert updated.updated_at >= original.updated_at

    def test_all_fields_together(self, _db_setup):
        db, brief, run = _db_setup
        post = _make_post(brief.id, post_id="all-fields")
        db.save_draft(post, run.id)
        pub_time = datetime(2025, 3, 4, 15, 0, tzinfo=UTC)

        db.update_publish_status(
            post.id,
            PublishStatus.published,
            published_at=pub_time,
            post_url="https://example.com/post",
            platform_post_id="ext-789",
        )

        updated = db.get_post(post.id)
        assert updated.publish_status == PublishStatus.published
        assert updated.post_url == "https://example.com/post"
        assert updated.platform_post_id == "ext-789"


# ---------------------------------------------------------------------------
# save_publish_log / get_publish_history
# ---------------------------------------------------------------------------


class TestSavePublishLog:
    def test_saves_success_entry(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="log-post-1",
            platform_post_id="plat-id-1",
            post_url="https://twitter.com/post/1",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert len(history) == 1
        assert history[0]["post_id"] == "log-post-1"
        assert history[0]["status"] == "published"

    def test_saves_failure_entry(self, tmp_db):
        result = PublishResult(
            success=False,
            platform=Platform.linkedin,
            post_id="log-fail-1",
            error="Connection refused",
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert len(history) == 1
        assert history[0]["status"] == "failed"
        assert history[0]["error"] == "Connection refused"

    def test_saves_platform(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.reddit,
            post_id="reddit-post",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert history[0]["platform"] == "reddit"

    def test_saves_post_url(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="url-post",
            post_url="https://twitter.com/status/999",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert history[0]["post_url"] == "https://twitter.com/status/999"

    def test_saves_platform_post_id(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="plat-log",
            platform_post_id="ext-id-42",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert history[0]["platform_post_id"] == "ext-id-42"

    def test_saves_published_at(self, tmp_db):
        ts = datetime(2025, 3, 4, 14, 30, tzinfo=UTC)
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="ts-log",
            published_at=ts,
        )

        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()
        assert history[0]["published_at"] == ts.isoformat()


class TestGetPublishHistory:
    def test_empty_returns_empty(self, tmp_db):
        assert tmp_db.get_publish_history() == []

    def test_returns_dicts(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="dict-test",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )
        tmp_db.save_publish_log(result)

        history = tmp_db.get_publish_history()

        assert isinstance(history[0], dict)

    def test_ordered_by_published_at_desc(self, tmp_db):
        r1 = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="old",
            published_at=datetime(2025, 3, 3, 10, 0, tzinfo=UTC),
        )
        r2 = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="new",
            published_at=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        tmp_db.save_publish_log(r1)
        tmp_db.save_publish_log(r2)

        history = tmp_db.get_publish_history()

        assert len(history) == 2
        assert history[0]["post_id"] == "new"
        assert history[1]["post_id"] == "old"

    def test_limit_parameter(self, tmp_db):
        for i in range(5):
            r = PublishResult(
                success=True,
                platform=Platform.twitter,
                post_id=f"limit-{i}",
                published_at=datetime(2025, 3, 4, 10 + i, 0, tzinfo=UTC),
            )
            tmp_db.save_publish_log(r)

        history = tmp_db.get_publish_history(limit=2)

        assert len(history) == 2

    def test_default_limit_is_20(self, tmp_db):
        for i in range(25):
            r = PublishResult(
                success=True,
                platform=Platform.twitter,
                post_id=f"def-{i}",
                published_at=datetime(2025, 3, 4, 0, i, tzinfo=UTC),
            )
            tmp_db.save_publish_log(r)

        history = tmp_db.get_publish_history()

        assert len(history) == 20

    def test_history_contains_all_fields(self, tmp_db):
        result = PublishResult(
            success=True,
            platform=Platform.linkedin,
            post_id="full-log",
            platform_post_id="li-42",
            post_url="https://linkedin.com/post/42",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )
        tmp_db.save_publish_log(result)

        entry = tmp_db.get_publish_history()[0]

        assert "id" in entry
        assert entry["post_id"] == "full-log"
        assert entry["platform"] == "linkedin"
        assert entry["status"] == "published"
        assert entry["platform_post_id"] == "li-42"
        assert entry["post_url"] == "https://linkedin.com/post/42"
        assert entry["published_at"] is not None
        assert entry["error"] is None


# ---------------------------------------------------------------------------
# publish_log table exists
# ---------------------------------------------------------------------------


class TestPublishLogSchema:
    def test_publish_log_table_exists(self, tmp_db):
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='publish_log'"
        ).fetchone()
        assert row is not None

    def test_publish_log_post_index_exists(self, tmp_db):
        conn = tmp_db._get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_publish_log_post'"
        ).fetchone()
        assert row is not None

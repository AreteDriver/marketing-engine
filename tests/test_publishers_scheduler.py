"""Tests for marketing_engine.publishers.scheduler."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform, PublishStatus
from marketing_engine.exceptions import PublishError
from marketing_engine.models import PostDraft
from marketing_engine.publishers.result import PublishResult
from marketing_engine.publishers.scheduler import publish_due_posts, publish_single


def _make_post(
    post_id: str = "post-1",
    platform: Platform = Platform.twitter,
    approval_status: ApprovalStatus = ApprovalStatus.approved,
    publish_status: PublishStatus = PublishStatus.pending,
    scheduled_time: datetime | None = None,
) -> PostDraft:
    return PostDraft(
        id=post_id,
        brief_id="brief-1",
        stream=ContentStream.project_marketing,
        platform=platform,
        content="Test post content.",
        approval_status=approval_status,
        publish_status=publish_status,
        scheduled_time=scheduled_time or datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
    )


def _success_result(post: PostDraft) -> PublishResult:
    return PublishResult(
        success=True,
        platform=post.platform,
        post_id=post.id,
        platform_post_id="plat-123",
        post_url="https://example.com/post/123",
        published_at=datetime(2025, 3, 4, 14, 5, tzinfo=UTC),
    )


def _failure_result(post: PostDraft, error: str = "API error") -> PublishResult:
    return PublishResult(
        success=False,
        platform=post.platform,
        post_id=post.id,
        error=error,
    )


# ---------------------------------------------------------------------------
# publish_due_posts
# ---------------------------------------------------------------------------


class TestPublishDuePostsEmpty:
    def test_no_publishable_returns_empty(self):
        db = MagicMock()
        db.get_publishable.return_value = []

        results = publish_due_posts(db, dry_run=True)

        assert results == []

    def test_calls_get_publishable_with_now(self):
        db = MagicMock()
        db.get_publishable.return_value = []
        now = datetime(2025, 3, 4, 14, 0, tzinfo=UTC)

        publish_due_posts(db, now=now)

        db.get_publishable.assert_called_once_with(now)

    def test_uses_utcnow_when_now_is_none(self):
        db = MagicMock()
        db.get_publishable.return_value = []

        publish_due_posts(db)

        args = db.get_publishable.call_args[0]
        assert args[0].tzinfo is not None  # has timezone


class TestPublishDuePostsSuccess:
    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_publishes_each_post(self, mock_get_pub):
        post1 = _make_post(post_id="p1")
        post2 = _make_post(post_id="p2", platform=Platform.linkedin)

        mock_pub = MagicMock()
        mock_pub.publish.side_effect = [_success_result(post1), _success_result(post2)]
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post1, post2]

        results = publish_due_posts(db, dry_run=True, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        assert len(results) == 2
        assert all(r.success for r in results)

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_updates_db_status_on_success(self, mock_get_pub):
        post = _make_post()
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        db.update_publish_status.assert_called_once_with(
            post.id,
            PublishStatus.published,
            published_at=result.published_at,
            post_url=result.post_url,
            platform_post_id=result.platform_post_id,
        )

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_saves_publish_log_on_success(self, mock_get_pub):
        post = _make_post()
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        db.save_publish_log.assert_called_once_with(result)

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_passes_dry_run_to_get_publisher(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.return_value = _success_result(post)
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        publish_due_posts(db, dry_run=True, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        mock_get_pub.assert_called_once_with(post.platform, dry_run=True)


class TestPublishDuePostsFailure:
    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_publish_error_creates_failure_result(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("Twitter API down")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        results = publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        assert len(results) == 1
        assert results[0].success is False
        assert "Twitter API down" in results[0].error

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_updates_db_with_failed_status(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("rate limit")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        db.update_publish_status.assert_called_once_with(
            post.id,
            PublishStatus.failed,
            publish_error="rate limit",
        )

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_saves_publish_log_on_failure(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("error")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        db.save_publish_log.assert_called_once()
        logged = db.save_publish_log.call_args[0][0]
        assert logged.success is False


class TestPublishDuePostsMixed:
    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_mixed_success_and_failure(self, mock_get_pub):
        post1 = _make_post(post_id="ok-1")
        post2 = _make_post(post_id="fail-1")

        mock_pub = MagicMock()
        mock_pub.publish.side_effect = [
            _success_result(post1),
            PublishError("API error"),
        ]
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post1, post2]

        results = publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_continues_after_failure(self, mock_get_pub):
        post1 = _make_post(post_id="fail-first")
        post2 = _make_post(post_id="ok-second")

        mock_pub = MagicMock()
        mock_pub.publish.side_effect = [
            PublishError("first fails"),
            _success_result(post2),
        ]
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post1, post2]

        results = publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        assert len(results) == 2
        assert db.update_publish_status.call_count == 2
        assert db.save_publish_log.call_count == 2

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_result_platform_matches_post(self, mock_get_pub):
        post = _make_post(platform=Platform.reddit)
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("fail")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_publishable.return_value = [post]

        results = publish_due_posts(db, now=datetime(2025, 3, 4, 15, 0, tzinfo=UTC))

        assert results[0].platform == Platform.reddit


# ---------------------------------------------------------------------------
# publish_single
# ---------------------------------------------------------------------------


class TestPublishSingleNotFound:
    def test_raises_publish_error_when_post_not_found(self):
        db = MagicMock()
        db.get_post.return_value = None

        with pytest.raises(PublishError, match="Post not found"):
            publish_single(db, "nonexistent-id")

    def test_error_includes_post_id(self):
        db = MagicMock()
        db.get_post.return_value = None

        with pytest.raises(PublishError, match="abc-123"):
            publish_single(db, "abc-123")


class TestPublishSingleNotApproved:
    def test_pending_post_raises(self):
        post = _make_post(approval_status=ApprovalStatus.pending)
        db = MagicMock()
        db.get_post.return_value = post

        with pytest.raises(PublishError, match="not approved"):
            publish_single(db, post.id)

    def test_rejected_post_raises(self):
        post = _make_post(approval_status=ApprovalStatus.rejected)
        db = MagicMock()
        db.get_post.return_value = post

        with pytest.raises(PublishError, match="not approved"):
            publish_single(db, post.id)

    def test_error_includes_current_status(self):
        post = _make_post(approval_status=ApprovalStatus.rejected)
        db = MagicMock()
        db.get_post.return_value = post

        with pytest.raises(PublishError, match="rejected"):
            publish_single(db, post.id)


class TestPublishSingleApproved:
    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_approved_post_succeeds(self, mock_get_pub):
        post = _make_post(approval_status=ApprovalStatus.approved)
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        ret = publish_single(db, post.id)

        assert ret.success is True

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_edited_post_succeeds(self, mock_get_pub):
        post = _make_post(approval_status=ApprovalStatus.edited)
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        ret = publish_single(db, post.id)

        assert ret.success is True

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_updates_db_status_on_success(self, mock_get_pub):
        post = _make_post()
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        publish_single(db, post.id)

        db.update_publish_status.assert_called_once_with(
            post.id,
            PublishStatus.published,
            published_at=result.published_at,
            post_url=result.post_url,
            platform_post_id=result.platform_post_id,
        )

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_saves_publish_log(self, mock_get_pub):
        post = _make_post()
        result = _success_result(post)
        mock_pub = MagicMock()
        mock_pub.publish.return_value = result
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        publish_single(db, post.id)

        db.save_publish_log.assert_called_once_with(result)

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_passes_dry_run_flag(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.return_value = _success_result(post)
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        publish_single(db, post.id, dry_run=True)

        mock_get_pub.assert_called_once_with(post.platform, dry_run=True)


class TestPublishSingleFailure:
    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_publish_error_returns_failure_result(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("network timeout")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        result = publish_single(db, post.id)

        assert result.success is False
        assert "network timeout" in result.error

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_updates_db_with_failed_status(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("bad request")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        publish_single(db, post.id)

        db.update_publish_status.assert_called_once_with(
            post.id,
            PublishStatus.failed,
            publish_error="bad request",
        )

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_saves_publish_log_on_failure(self, mock_get_pub):
        post = _make_post()
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("fail")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        publish_single(db, post.id)

        db.save_publish_log.assert_called_once()
        logged = db.save_publish_log.call_args[0][0]
        assert logged.success is False

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_failure_result_has_post_id(self, mock_get_pub):
        post = _make_post(post_id="my-post")
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("fail")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        result = publish_single(db, post.id)

        assert result.post_id == "my-post"

    @patch("marketing_engine.publishers.scheduler.get_publisher")
    def test_failure_result_has_platform(self, mock_get_pub):
        post = _make_post(platform=Platform.linkedin)
        mock_pub = MagicMock()
        mock_pub.publish.side_effect = PublishError("fail")
        mock_get_pub.return_value = mock_pub

        db = MagicMock()
        db.get_post.return_value = post

        result = publish_single(db, post.id)

        assert result.platform == Platform.linkedin

"""Tests for marketing_engine.approval."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from marketing_engine.approval import (
    approve_post,
    edit_post,
    get_approval_summary,
    get_review_queue,
    reject_post,
)
from marketing_engine.enums import ApprovalStatus, ContentStream, Platform
from marketing_engine.exceptions import DatabaseError
from marketing_engine.models import PostDraft


def _insert_post(db, post: PostDraft, run_id: str) -> str:
    """Helper — save a post draft into the database and return its ID."""
    return db.save_draft(post, run_id)


def _seed_db(db, sample_brief, sample_pipeline_run, posts: list[PostDraft]) -> str:
    """Seed the database with a pipeline run, brief, and posts. Return run ID."""
    run_id = db.save_pipeline_run(sample_pipeline_run)
    db.save_brief(sample_brief, run_id)
    for post in posts:
        _insert_post(db, post, run_id)
    return run_id


def _make_post(
    brief_id: str,
    *,
    scheduled_time: datetime | None = None,
    approval_status: ApprovalStatus = ApprovalStatus.pending,
    platform: Platform = Platform.twitter,
    stream: ContentStream = ContentStream.project_marketing,
    content: str = "Test post content.",
) -> PostDraft:
    """Build a PostDraft with sensible defaults."""
    return PostDraft(
        brief_id=brief_id,
        stream=stream,
        platform=platform,
        content=content,
        hashtags=["test"],
        cta_url="https://example.com",
        scheduled_time=scheduled_time or datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        approval_status=approval_status,
    )


# ---------------------------------------------------------------------------
# approve_post
# ---------------------------------------------------------------------------


class TestApprovePost:
    def test_changes_status_to_approved(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = approve_post(tmp_db, post.id)

        assert result.approval_status == ApprovalStatus.approved

    def test_returns_updated_post_draft(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = approve_post(tmp_db, post.id)

        assert isinstance(result, PostDraft)
        assert result.id == post.id

    def test_pending_to_approved_transition(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id, approval_status=ApprovalStatus.pending)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        before = tmp_db.get_post(post.id)
        assert before.approval_status == ApprovalStatus.pending

        approve_post(tmp_db, post.id)

        after = tmp_db.get_post(post.id)
        assert after.approval_status == ApprovalStatus.approved

    def test_nonexistent_post_raises_database_error(self, tmp_db):
        with pytest.raises(DatabaseError, match="Post not found"):
            approve_post(tmp_db, "nonexistent-id-1234")


# ---------------------------------------------------------------------------
# edit_post
# ---------------------------------------------------------------------------


class TestEditPost:
    def test_changes_status_to_edited(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = edit_post(tmp_db, post.id, "Revised content here.")

        assert result.approval_status == ApprovalStatus.edited

    def test_sets_edited_content(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = edit_post(tmp_db, post.id, "Revised content here.")

        assert result.edited_content == "Revised content here."

    def test_returns_post_draft(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = edit_post(tmp_db, post.id, "New content")

        assert isinstance(result, PostDraft)
        assert result.id == post.id


# ---------------------------------------------------------------------------
# reject_post
# ---------------------------------------------------------------------------


class TestRejectPost:
    def test_changes_status_to_rejected(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = reject_post(tmp_db, post.id, reason="Off-brand")

        assert result.approval_status == ApprovalStatus.rejected

    def test_sets_rejection_reason(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = reject_post(tmp_db, post.id, reason="Off-brand")

        assert result.rejection_reason == "Off-brand"

    def test_reject_without_reason(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = reject_post(tmp_db, post.id)

        assert result.approval_status == ApprovalStatus.rejected
        assert result.rejection_reason is None

    def test_pending_to_rejected_transition(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id, approval_status=ApprovalStatus.pending)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        before = tmp_db.get_post(post.id)
        assert before.approval_status == ApprovalStatus.pending

        reject_post(tmp_db, post.id, reason="Duplicate")

        after = tmp_db.get_post(post.id)
        assert after.approval_status == ApprovalStatus.rejected
        assert after.rejection_reason == "Duplicate"


# ---------------------------------------------------------------------------
# get_review_queue
# ---------------------------------------------------------------------------


class TestGetReviewQueue:
    def test_returns_only_pending_posts(self, tmp_db, sample_brief, sample_pipeline_run):
        pending = _make_post(sample_brief.id, content="Pending post")
        approved = _make_post(
            sample_brief.id,
            content="Approved post",
            approval_status=ApprovalStatus.approved,
        )
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [pending, approved])

        queue = get_review_queue(tmp_db)

        assert len(queue) == 1
        assert queue[0].id == pending.id

    def test_week_of_filter(self, tmp_db, sample_brief, sample_pipeline_run):
        # Post in target week (2025-03-03 through 2025-03-09)
        in_week = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        # Post outside target week
        out_of_week = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 11, 10, 0, tzinfo=UTC),
        )
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [in_week, out_of_week])

        queue = get_review_queue(tmp_db, week_of=date(2025, 3, 3))

        assert len(queue) == 1
        assert queue[0].id == in_week.id


# ---------------------------------------------------------------------------
# get_approval_summary
# ---------------------------------------------------------------------------


class TestGetApprovalSummary:
    def test_counts_by_status(self, tmp_db, sample_brief, sample_pipeline_run):
        posts = [
            _make_post(sample_brief.id, approval_status=ApprovalStatus.pending),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.pending),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.approved),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.rejected),
        ]
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, posts)

        summary = get_approval_summary(tmp_db)

        assert summary["pending"] == 2
        assert summary["approved"] == 1
        assert summary["rejected"] == 1
        assert summary["edited"] == 0
        assert summary["total"] == 4

    def test_no_posts_returns_all_zeros(self, tmp_db):
        summary = get_approval_summary(tmp_db)

        assert summary["pending"] == 0
        assert summary["approved"] == 0
        assert summary["edited"] == 0
        assert summary["rejected"] == 0
        assert summary["total"] == 0

    def test_summary_with_week_of(self, tmp_db, sample_brief, sample_pipeline_run):
        in_week = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 5, 12, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.approved,
        )
        out_of_week = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 12, 12, 0, tzinfo=UTC),
            approval_status=ApprovalStatus.pending,
        )
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [in_week, out_of_week])

        summary = get_approval_summary(tmp_db, week_of=date(2025, 3, 3))

        assert summary["approved"] == 1
        assert summary["total"] == 1

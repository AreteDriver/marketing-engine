"""Post approval workflow functions."""

from __future__ import annotations

from datetime import date

from marketing_engine.db import Database
from marketing_engine.enums import ApprovalStatus
from marketing_engine.exceptions import DatabaseError
from marketing_engine.models import PostDraft


def get_review_queue(db: Database, week_of: date | None = None) -> list[PostDraft]:
    """Return all pending posts for review.

    Args:
        db: Database instance.
        week_of: Optional week filter (Monday date).

    Returns:
        List of PostDraft objects with pending status.
    """
    return db.get_pending(week_of=week_of)


def approve_post(db: Database, post_id: str) -> PostDraft:
    """Approve a post for publishing.

    Args:
        db: Database instance.
        post_id: The post ID to approve.

    Returns:
        The updated PostDraft.

    Raises:
        DatabaseError: If the post is not found.
    """
    db.update_approval(post_id, ApprovalStatus.approved)
    post = db.get_post(post_id)
    if post is None:
        raise DatabaseError(f"Post not found after approval: {post_id}")
    return post


def edit_post(db: Database, post_id: str, new_content: str) -> PostDraft:
    """Edit a post's content and mark as edited.

    Args:
        db: Database instance.
        post_id: The post ID to edit.
        new_content: The revised content.

    Returns:
        The updated PostDraft.

    Raises:
        DatabaseError: If the post is not found.
    """
    db.update_approval(post_id, ApprovalStatus.edited, edited_content=new_content)
    post = db.get_post(post_id)
    if post is None:
        raise DatabaseError(f"Post not found after edit: {post_id}")
    return post


def reject_post(db: Database, post_id: str, reason: str | None = None) -> PostDraft:
    """Reject a post with an optional reason.

    Args:
        db: Database instance.
        post_id: The post ID to reject.
        reason: Optional rejection reason.

    Returns:
        The updated PostDraft.

    Raises:
        DatabaseError: If the post is not found.
    """
    db.update_approval(post_id, ApprovalStatus.rejected, rejection_reason=reason)
    post = db.get_post(post_id)
    if post is None:
        raise DatabaseError(f"Post not found after rejection: {post_id}")
    return post


def get_approval_summary(db: Database, week_of: date | None = None) -> dict:
    """Return approval status counts.

    Args:
        db: Database instance.
        week_of: Optional week filter.

    Returns:
        Dict with counts keyed by status name, plus a "total" key.
    """
    if week_of is not None:
        all_posts = db.get_queue(week_of)
    else:
        # Get all pending + use a broad query
        all_posts = db.get_pending(week_of=None)
        # Also need non-pending — query all statuses
        conn = db._get_conn()
        rows = conn.execute("SELECT * FROM post_drafts ORDER BY scheduled_time").fetchall()
        all_posts = [db._row_to_post(r) for r in rows]

    counts: dict[str, int] = {
        "pending": 0,
        "approved": 0,
        "edited": 0,
        "rejected": 0,
        "total": 0,
    }
    for post in all_posts:
        status_key = post.approval_status.value
        counts[status_key] = counts.get(status_key, 0) + 1
        counts["total"] += 1
    return counts

"""Scheduler for publishing due posts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from marketing_engine.db import Database
from marketing_engine.enums import PublishStatus
from marketing_engine.exceptions import PublishError
from marketing_engine.publishers.base import get_publisher
from marketing_engine.publishers.result import PublishResult

logger = logging.getLogger(__name__)


def publish_due_posts(
    db: Database,
    dry_run: bool = False,
    now: datetime | None = None,
) -> list[PublishResult]:
    """Publish all approved posts that are due.

    Args:
        db: Database instance.
        dry_run: If True, use DryRunPublisher.
        now: Override current time (for testing).

    Returns:
        List of publish results.
    """
    if now is None:
        now = datetime.now(UTC)

    publishable = db.get_publishable(now)
    results: list[PublishResult] = []

    for post in publishable:
        try:
            publisher = get_publisher(post.platform, dry_run=dry_run)
            result = publisher.publish(post)
        except PublishError as exc:
            result = PublishResult(
                success=False,
                platform=post.platform,
                post_id=post.id,
                error=str(exc),
            )

        # Update post status in DB
        if result.success:
            db.update_publish_status(
                post.id,
                PublishStatus.published,
                published_at=result.published_at,
                post_url=result.post_url,
                platform_post_id=result.platform_post_id,
            )
        else:
            db.update_publish_status(
                post.id,
                PublishStatus.failed,
                publish_error=result.error,
            )

        # Record in publish log
        db.save_publish_log(result)
        results.append(result)

    return results


def publish_single(
    db: Database,
    post_id: str,
    dry_run: bool = False,
) -> PublishResult:
    """Publish a single post by ID.

    Args:
        db: Database instance.
        post_id: The post to publish.
        dry_run: If True, use DryRunPublisher.

    Returns:
        Publish result.

    Raises:
        PublishError: If the post is not found or not publishable.
    """
    post = db.get_post(post_id)
    if post is None:
        raise PublishError(f"Post not found: {post_id}")

    if post.approval_status.value not in ("approved", "edited"):
        raise PublishError(f"Post {post_id} is not approved (status: {post.approval_status})")

    try:
        publisher = get_publisher(post.platform, dry_run=dry_run)
        result = publisher.publish(post)
    except PublishError as exc:
        result = PublishResult(
            success=False,
            platform=post.platform,
            post_id=post.id,
            error=str(exc),
        )

    if result.success:
        db.update_publish_status(
            post.id,
            PublishStatus.published,
            published_at=result.published_at,
            post_url=result.post_url,
            platform_post_id=result.platform_post_id,
        )
    else:
        db.update_publish_status(
            post.id,
            PublishStatus.failed,
            publish_error=result.error,
        )

    db.save_publish_log(result)
    return result

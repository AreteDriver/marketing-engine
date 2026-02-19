"""Export approved posts to JSON or Markdown format."""

from __future__ import annotations

import json
from datetime import date
from itertools import groupby

from marketing_engine.db import Database
from marketing_engine.enums import ApprovalStatus
from marketing_engine.models import PostDraft


def export_approved(db: Database, week_of: date, fmt: str = "json") -> str:
    """Export approved and edited posts for a given week.

    Args:
        db: Database instance.
        week_of: The Monday of the target week.
        fmt: Output format — "json" or "markdown".

    Returns:
        Formatted string of exported posts.
    """
    all_posts = db.get_queue(week_of)
    approved = [
        p
        for p in all_posts
        if p.approval_status in (ApprovalStatus.approved, ApprovalStatus.edited)
    ]

    if fmt == "markdown":
        return _export_markdown(approved)
    return _export_json(approved)


def _export_json(posts: list[PostDraft]) -> str:
    """Export posts as a JSON array.

    Uses the effective content (edited_content if available, else content).
    """
    items = []
    for post in posts:
        effective_content = post.edited_content or post.content
        items.append(
            {
                "id": post.id,
                "platform": post.platform.value,
                "stream": post.stream.value,
                "content": effective_content,
                "cta_url": post.cta_url,
                "hashtags": post.hashtags,
                "subreddit": post.subreddit,
                "scheduled_time": (
                    post.scheduled_time.isoformat() if post.scheduled_time else None
                ),
                "status": post.approval_status.value,
            }
        )
    return json.dumps(items, indent=2)


def _export_markdown(posts: list[PostDraft]) -> str:
    """Export posts as markdown grouped by day with platform badges."""
    if not posts:
        return "# Weekly Content Queue\n\nNo approved posts for this week.\n"

    # Sort by scheduled time
    sorted_posts = sorted(
        posts,
        key=lambda p: p.scheduled_time.isoformat() if p.scheduled_time else "",
    )

    lines = ["# Weekly Content Queue", ""]

    # Group by day
    def day_key(post: PostDraft) -> str:
        if post.scheduled_time:
            return post.scheduled_time.strftime("%A, %B %d")
        return "Unscheduled"

    for day, day_posts in groupby(sorted_posts, key=day_key):
        lines.append(f"## {day}")
        lines.append("")

        for post in day_posts:
            platform_badge = f"[{post.platform.value.upper()}]"
            stream_badge = f"({post.stream.value})"
            time_str = post.scheduled_time.strftime("%I:%M %p") if post.scheduled_time else "TBD"
            effective_content = post.edited_content or post.content

            lines.append(f"### {time_str} {platform_badge} {stream_badge}")
            lines.append("")
            lines.append(effective_content)
            lines.append("")

            if post.hashtags:
                tags = " ".join(
                    f"#{tag}" if not tag.startswith("#") else tag for tag in post.hashtags
                )
                lines.append(f"**Tags:** {tags}")
                lines.append("")

            if post.cta_url:
                lines.append(f"**CTA:** {post.cta_url}")
                lines.append("")

            if post.subreddit:
                lines.append(f"**Subreddit:** r/{post.subreddit}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)

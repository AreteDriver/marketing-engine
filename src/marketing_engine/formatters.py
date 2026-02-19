"""Rich formatting utilities for CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from marketing_engine.enums import ApprovalStatus
from marketing_engine.models import PipelineRun, PostDraft

_STATUS_COLORS = {
    ApprovalStatus.pending: "yellow",
    ApprovalStatus.approved: "green",
    ApprovalStatus.edited: "cyan",
    ApprovalStatus.rejected: "red",
}


def format_queue_table(posts: list[PostDraft], console: Console) -> None:
    """Display a Rich table of queued posts.

    Columns: Day, Time, Platform, Stream, Content (truncated), Status.
    """
    table = Table(title="Content Queue", show_lines=True)
    table.add_column("Day", style="bold", min_width=10)
    table.add_column("Time", min_width=8)
    table.add_column("Platform", min_width=8)
    table.add_column("Stream", min_width=12)
    table.add_column("Content", min_width=30, max_width=50)
    table.add_column("Status", min_width=8)

    # Sort by scheduled time
    sorted_posts = sorted(
        posts,
        key=lambda p: p.scheduled_time.isoformat() if p.scheduled_time else "",
    )

    for post in sorted_posts:
        if post.scheduled_time:
            day = post.scheduled_time.strftime("%a %m/%d")
            time_str = post.scheduled_time.strftime("%I:%M %p")
        else:
            day = "TBD"
            time_str = "TBD"

        # Truncate content to 50 chars
        content = post.edited_content or post.content
        if len(content) > 50:
            content = content[:47] + "..."

        color = _STATUS_COLORS.get(post.approval_status, "white")
        status_text = Text(post.approval_status.value, style=color)

        table.add_row(
            day,
            time_str,
            post.platform.value,
            post.stream.value,
            content,
            status_text,
        )

    console.print(table)


def format_post_detail(post: PostDraft, console: Console) -> None:
    """Display a Rich panel with full post details."""
    effective_content = post.edited_content or post.content

    lines = [
        f"[bold]Platform:[/bold] {post.platform.value}",
        f"[bold]Stream:[/bold] {post.stream.value}",
        f"[bold]Status:[/bold] [{_STATUS_COLORS.get(post.approval_status, 'white')}]"
        f"{post.approval_status.value}[/]",
        "",
        "[bold]Content:[/bold]",
        effective_content,
    ]

    if post.hashtags:
        tags = " ".join(f"#{tag}" if not tag.startswith("#") else tag for tag in post.hashtags)
        lines.extend(["", f"[bold]Hashtags:[/bold] {tags}"])

    if post.cta_url:
        lines.extend(["", f"[bold]CTA:[/bold] {post.cta_url}"])

    if post.subreddit:
        lines.extend(["", f"[bold]Subreddit:[/bold] r/{post.subreddit}"])

    if post.scheduled_time:
        time_str = post.scheduled_time.strftime("%A, %B %d at %I:%M %p")
        lines.extend(["", f"[bold]Scheduled:[/bold] {time_str}"])

    if post.rejection_reason:
        lines.extend(
            [
                "",
                f"[bold red]Rejection reason:[/bold red] {post.rejection_reason}",
            ]
        )

    body = "\n".join(lines)
    panel = Panel(
        body,
        title=f"Post {post.id[:8]}...",
        subtitle=post.platform.value,
        expand=True,
    )
    console.print(panel)


def format_pipeline_summary(run: PipelineRun, console: Console) -> None:
    """Display a Rich summary of a pipeline run."""
    status_color = "green" if run.status == "completed" else "red"

    table = Table(title="Pipeline Run Summary", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Run ID", run.id[:8] + "...")
    table.add_row("Week Of", run.week_of.isoformat())
    table.add_row("Status", Text(run.status, style=status_color))
    table.add_row("Briefs Generated", str(run.briefs_count))
    table.add_row("Drafts Created", str(run.drafts_count))
    table.add_row("Posts Scheduled", str(run.posts_count))
    table.add_row("Started", run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC"))

    if run.completed_at:
        table.add_row(
            "Completed",
            run.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        duration = run.completed_at - run.started_at
        table.add_row("Duration", f"{duration.total_seconds():.1f}s")

    if run.error:
        table.add_row("Error", Text(run.error, style="red"))

    console.print(table)

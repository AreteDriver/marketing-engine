"""Tests for marketing_engine.formatters."""

from __future__ import annotations

from datetime import UTC, date, datetime
from io import StringIO

from rich.console import Console

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform
from marketing_engine.formatters import (
    format_pipeline_summary,
    format_post_detail,
    format_queue_table,
)
from marketing_engine.models import PipelineRun, PostDraft


def _make_post(
    *,
    scheduled_time: datetime | None = None,
    approval_status: ApprovalStatus = ApprovalStatus.pending,
    platform: Platform = Platform.twitter,
    stream: ContentStream = ContentStream.project_marketing,
    content: str = "Test post content for formatting.",
    edited_content: str | None = None,
    hashtags: list[str] | None = None,
    cta_url: str = "https://example.com",
    rejection_reason: str | None = None,
    subreddit: str | None = None,
) -> PostDraft:
    """Build a PostDraft with sensible defaults for formatter tests."""
    return PostDraft(
        brief_id="brief-001",
        stream=stream,
        platform=platform,
        content=content,
        hashtags=hashtags or [],
        cta_url=cta_url,
        subreddit=subreddit,
        scheduled_time=scheduled_time,
        approval_status=approval_status,
        edited_content=edited_content,
        rejection_reason=rejection_reason,
    )


def _capture_console() -> Console:
    """Create a Console that writes to a StringIO buffer."""
    return Console(file=StringIO(), force_terminal=True, width=120)


def _get_output(console: Console) -> str:
    """Extract the captured output string from the console."""
    return console.file.getvalue()


# ---------------------------------------------------------------------------
# format_queue_table
# ---------------------------------------------------------------------------


class TestFormatQueueTable:
    def test_outputs_table_with_column_headers(self):
        post = _make_post(scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC))
        console = _capture_console()

        format_queue_table([post], console)
        output = _get_output(console)

        assert "Content Queue" in output
        assert "Platform" in output
        assert "Stream" in output
        assert "Status" in output

    def test_includes_truncated_content(self):
        long_content = "A" * 80  # Longer than 50 chars — should be truncated
        post = _make_post(
            content=long_content,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        )
        console = _capture_console()

        format_queue_table([post], console)
        output = _get_output(console)

        # Truncated to 47 chars + "..."
        assert "..." in output
        # Full 80-char string should NOT appear
        assert long_content not in output

    def test_sorts_by_scheduled_time(self):
        later = _make_post(
            content="Later post",
            scheduled_time=datetime(2025, 3, 4, 17, 0, tzinfo=UTC),
        )
        earlier = _make_post(
            content="Earlier post",
            scheduled_time=datetime(2025, 3, 4, 9, 0, tzinfo=UTC),
        )
        console = _capture_console()

        format_queue_table([later, earlier], console)
        output = _get_output(console)

        # Earlier should appear before later in the output
        earlier_pos = output.find("Earlier post")
        later_pos = output.find("Later post")
        assert earlier_pos < later_pos

    def test_handles_no_scheduled_time(self):
        post = _make_post(scheduled_time=None)
        console = _capture_console()

        format_queue_table([post], console)
        output = _get_output(console)

        assert "TBD" in output


# ---------------------------------------------------------------------------
# format_post_detail
# ---------------------------------------------------------------------------


class TestFormatPostDetail:
    def test_shows_platform_stream_status(self):
        post = _make_post(platform=Platform.linkedin, stream=ContentStream.eve_content)
        console = _capture_console()

        format_post_detail(post, console)
        output = _get_output(console)

        assert "linkedin" in output
        assert "eve_content" in output
        assert "pending" in output

    def test_shows_edited_content_when_available(self):
        post = _make_post(
            content="Original",
            edited_content="Revised version",
        )
        console = _capture_console()

        format_post_detail(post, console)
        output = _get_output(console)

        assert "Revised version" in output

    def test_shows_hashtags_and_cta(self):
        post = _make_post(
            hashtags=["python", "dev"],
            cta_url="https://example.com/action",
        )
        console = _capture_console()

        format_post_detail(post, console)
        output = _get_output(console)

        assert "#python" in output
        assert "#dev" in output
        assert "https://example.com/action" in output

    def test_shows_rejection_reason(self):
        post = _make_post(
            approval_status=ApprovalStatus.rejected,
            rejection_reason="Off-brand messaging",
        )
        console = _capture_console()

        format_post_detail(post, console)
        output = _get_output(console)

        assert "Off-brand messaging" in output


# ---------------------------------------------------------------------------
# format_pipeline_summary
# ---------------------------------------------------------------------------


class TestFormatPipelineSummary:
    def test_shows_run_id_week_status_counts(self):
        run = PipelineRun(
            week_of=date(2025, 3, 3),
            status="completed",
            briefs_count=5,
            drafts_count=10,
            posts_count=8,
            completed_at=datetime(2025, 3, 3, 12, 30, 0, tzinfo=UTC),
        )
        console = _capture_console()

        format_pipeline_summary(run, console)
        output = _get_output(console)

        assert "Pipeline Run Summary" in output
        assert "2025-03-03" in output
        assert "completed" in output
        assert "5" in output  # briefs_count
        assert "10" in output  # drafts_count
        assert "8" in output  # posts_count

    def test_shows_error_when_present(self):
        run = PipelineRun(
            week_of=date(2025, 3, 3),
            status="failed",
            error="LLM timeout after 30s",
        )
        console = _capture_console()

        format_pipeline_summary(run, console)
        output = _get_output(console)

        assert "LLM timeout after 30s" in output

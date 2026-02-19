"""Tests for marketing_engine.export."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform
from marketing_engine.export import _export_json, _export_markdown, export_approved
from marketing_engine.models import PostDraft


def _make_post(
    brief_id: str,
    *,
    scheduled_time: datetime | None = None,
    approval_status: ApprovalStatus = ApprovalStatus.approved,
    platform: Platform = Platform.twitter,
    stream: ContentStream = ContentStream.project_marketing,
    content: str = "Approved post content.",
    edited_content: str | None = None,
    hashtags: list[str] | None = None,
    cta_url: str = "https://example.com",
    subreddit: str | None = None,
) -> PostDraft:
    """Build a PostDraft with sensible defaults for export tests."""
    return PostDraft(
        brief_id=brief_id,
        stream=stream,
        platform=platform,
        content=content,
        hashtags=hashtags or ["test"],
        cta_url=cta_url,
        subreddit=subreddit,
        scheduled_time=scheduled_time or datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
        approval_status=approval_status,
        edited_content=edited_content,
    )


def _seed_db(db, sample_brief, sample_pipeline_run, posts: list[PostDraft]) -> str:
    """Seed database with a pipeline run, brief, and posts."""
    run_id = db.save_pipeline_run(sample_pipeline_run)
    db.save_brief(sample_brief, run_id)
    for post in posts:
        db.save_draft(post, run_id)
    return run_id


# ---------------------------------------------------------------------------
# export_approved (integration with DB)
# ---------------------------------------------------------------------------


class TestExportApproved:
    def test_json_format_returns_valid_json(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = export_approved(tmp_db, date(2025, 3, 3), fmt="json")
        parsed = json.loads(result)

        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_markdown_format_returns_string(self, tmp_db, sample_brief, sample_pipeline_run):
        post = _make_post(sample_brief.id)
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, [post])

        result = export_approved(tmp_db, date(2025, 3, 3), fmt="markdown")

        assert isinstance(result, str)
        assert "# Weekly Content Queue" in result

    def test_only_approved_and_edited_exported(self, tmp_db, sample_brief, sample_pipeline_run):
        posts = [
            _make_post(sample_brief.id, approval_status=ApprovalStatus.approved),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.edited),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.pending),
            _make_post(sample_brief.id, approval_status=ApprovalStatus.rejected),
        ]
        _seed_db(tmp_db, sample_brief, sample_pipeline_run, posts)

        result = export_approved(tmp_db, date(2025, 3, 3), fmt="json")
        parsed = json.loads(result)

        assert len(parsed) == 2
        statuses = {p["status"] for p in parsed}
        assert statuses == {"approved", "edited"}


# ---------------------------------------------------------------------------
# _export_json
# ---------------------------------------------------------------------------


class TestExportJson:
    def test_includes_all_expected_fields(self, sample_brief):
        post = _make_post(sample_brief.id, hashtags=["python", "cli"])
        result = json.loads(_export_json([post]))

        item = result[0]
        assert "id" in item
        assert "platform" in item
        assert "stream" in item
        assert "content" in item
        assert "cta_url" in item
        assert "hashtags" in item
        assert "scheduled_time" in item
        assert "status" in item

    def test_uses_edited_content_when_available(self, sample_brief):
        post = _make_post(
            sample_brief.id,
            content="Original content",
            edited_content="Edited content",
        )
        result = json.loads(_export_json([post]))

        assert result[0]["content"] == "Edited content"

    def test_uses_original_content_when_no_edit(self, sample_brief):
        post = _make_post(sample_brief.id, content="Original content")
        result = json.loads(_export_json([post]))

        assert result[0]["content"] == "Original content"

    def test_empty_list_returns_empty_json_array(self):
        result = _export_json([])
        assert result == "[]"


# ---------------------------------------------------------------------------
# _export_markdown
# ---------------------------------------------------------------------------


class TestExportMarkdown:
    def test_groups_by_day(self, sample_brief):
        post_tue = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 4, 10, 0, tzinfo=UTC),
            content="Tuesday post",
        )
        post_wed = _make_post(
            sample_brief.id,
            scheduled_time=datetime(2025, 3, 5, 14, 0, tzinfo=UTC),
            content="Wednesday post",
        )
        result = _export_markdown([post_tue, post_wed])

        assert "## Tuesday, March 04" in result
        assert "## Wednesday, March 05" in result

    def test_includes_platform_badge(self, sample_brief):
        post = _make_post(sample_brief.id, platform=Platform.linkedin)
        result = _export_markdown([post])

        assert "[LINKEDIN]" in result

    def test_includes_stream_badge(self, sample_brief):
        post = _make_post(sample_brief.id, stream=ContentStream.eve_content)
        result = _export_markdown([post])

        assert "(eve_content)" in result

    def test_includes_hashtags(self, sample_brief):
        post = _make_post(sample_brief.id, hashtags=["python", "dev"])
        result = _export_markdown([post])

        assert "#python" in result
        assert "#dev" in result

    def test_includes_cta(self, sample_brief):
        post = _make_post(sample_brief.id, cta_url="https://example.com/cta")
        result = _export_markdown([post])

        assert "**CTA:** https://example.com/cta" in result

    def test_empty_list_returns_no_approved_message(self):
        result = _export_markdown([])

        assert "No approved posts" in result

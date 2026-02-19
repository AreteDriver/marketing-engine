"""Tests for the ContentPipeline orchestrator."""

from __future__ import annotations

import json
from datetime import date

import pytest

from marketing_engine.db import Database
from marketing_engine.enums import ContentStream
from marketing_engine.exceptions import PipelineError
from marketing_engine.llm.base import MockLLMClient
from marketing_engine.models import PipelineRun
from marketing_engine.pipeline import ContentPipeline

WEEK_OF = date(2025, 3, 3)

CONFIG = {
    "brand_voice": {},
    "platform_rules": {},
    "schedule_rules": {"timezone": "UTC"},
}

# ---------------------------------------------------------------------------
# Mock responses — one per LLM call in order: research, draft, format (x N)
# ---------------------------------------------------------------------------

RESEARCH_RESPONSE = json.dumps(
    [
        {
            "topic": "Test Topic",
            "angle": "Test angle",
            "target_audience": "devs",
            "relevant_links": [],
            "stream": "project_marketing",
            "platforms": ["twitter", "linkedin"],
        }
    ]
)

DRAFT_RESPONSE = json.dumps(
    {
        "content": "Post text about testing.",
        "cta_url": "https://example.com",
        "hashtags": ["test"],
    }
)

FORMAT_RESPONSE = json.dumps(
    {
        "content": "Formatted post.",
        "hashtags": ["test"],
        "subreddit": None,
    }
)


def _mock_llm() -> MockLLMClient:
    """Return a MockLLMClient cycling: research -> draft -> format -> format."""
    return MockLLMClient([RESEARCH_RESPONSE, DRAFT_RESPONSE, FORMAT_RESPONSE, FORMAT_RESPONSE])


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestPipelineRun:
    """Tests for a successful pipeline run."""

    def test_run_returns_completed_pipeline_run(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        assert isinstance(result, PipelineRun)
        assert result.status == "completed"

    def test_run_saves_pipeline_run_to_db(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        pipeline.run(week_of=WEEK_OF)
        runs = tmp_db.get_pipeline_runs()
        assert len(runs) == 1
        assert runs[0].status == "completed"

    def test_run_saves_briefs_to_db(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        # Research returns 1 brief
        assert result.briefs_count == 1
        # Verify in DB — count briefs rows
        conn = tmp_db._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM content_briefs").fetchone()[0]
        assert count == 1

    def test_run_saves_drafts_to_db(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        conn = tmp_db._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM post_drafts").fetchone()[0]
        assert count == result.posts_count

    def test_run_sets_briefs_count(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        assert result.briefs_count == 1

    def test_run_sets_drafts_count(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        # 1 brief with 2 platforms (twitter + linkedin) -> 2 drafts
        assert result.drafts_count == 2

    def test_run_sets_posts_count(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        assert result.posts_count == 2

    def test_run_creates_posts_per_platform(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        pipeline.run(week_of=WEEK_OF)
        # Brief has platforms=["twitter", "linkedin"], so 2 posts
        conn = tmp_db._get_conn()
        platforms = {
            row[0] for row in conn.execute("SELECT DISTINCT platform FROM post_drafts").fetchall()
        }
        assert "twitter" in platforms
        assert "linkedin" in platforms

    def test_run_posts_have_scheduled_time(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        pipeline.run(week_of=WEEK_OF)
        conn = tmp_db._get_conn()
        rows = conn.execute("SELECT scheduled_time FROM post_drafts").fetchall()
        for row in rows:
            assert row[0] is not None, "scheduled_time should be set by queue stage"


# ---------------------------------------------------------------------------
# Streams & activity passthrough
# ---------------------------------------------------------------------------


class TestPipelineStreamFiltering:
    """Tests for stream and activity arguments."""

    def test_run_with_specific_streams(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        pipeline.run(week_of=WEEK_OF, streams=[ContentStream.project_marketing])
        # The research agent should have received stream values in user prompt
        system_prompt, user_prompt = llm.calls[0]
        assert "project_marketing" in user_prompt

    def test_run_with_activity(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        pipeline.run(week_of=WEEK_OF, activity="Shipped v2.0 with new API")
        system_prompt, user_prompt = llm.calls[0]
        assert "Shipped v2.0" in user_prompt


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestPipelineErrors:
    """Tests for pipeline error handling."""

    def test_run_on_llm_error_marks_failed(self, tmp_db: Database) -> None:
        # LLM returns invalid JSON that won't parse even on retry
        bad_llm = MockLLMClient(["not json at all"])
        pipeline = ContentPipeline(db=tmp_db, llm=bad_llm, config=CONFIG)
        with pytest.raises(PipelineError):
            pipeline.run(week_of=WEEK_OF)
        runs = tmp_db.get_pipeline_runs()
        assert len(runs) == 1
        assert runs[0].status == "failed"

    def test_run_on_llm_error_raises_pipeline_error(self, tmp_db: Database) -> None:
        bad_llm = MockLLMClient(["not valid json"])
        pipeline = ContentPipeline(db=tmp_db, llm=bad_llm, config=CONFIG)
        with pytest.raises(PipelineError, match="Pipeline failed"):
            pipeline.run(week_of=WEEK_OF)

    def test_run_completed_at_set_on_success(self, tmp_db: Database) -> None:
        llm = _mock_llm()
        pipeline = ContentPipeline(db=tmp_db, llm=llm, config=CONFIG)
        result = pipeline.run(week_of=WEEK_OF)
        assert result.completed_at is not None

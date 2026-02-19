"""Shared fixtures for marketing-engine tests."""

import json
from datetime import UTC, date, datetime

import pytest

from marketing_engine.db import Database
from marketing_engine.enums import ContentStream, Platform
from marketing_engine.llm.base import MockLLMClient
from marketing_engine.models import ContentBrief, PipelineRun, PostDraft


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary Database and close it after the test."""
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture()
def mock_llm():
    """Return a MockLLMClient with canned responses for research, draft, and format stages."""
    responses = [
        json.dumps(
            [
                {
                    "topic": "Test Topic",
                    "angle": "Test angle",
                    "target_audience": "developers",
                    "relevant_links": [],
                    "stream": "project_marketing",
                    "platforms": ["twitter", "linkedin"],
                }
            ]
        ),
        json.dumps(
            {
                "content": "Test post content here.",
                "cta_url": "https://example.com",
                "hashtags": ["test", "dev"],
            }
        ),
        json.dumps(
            {
                "content": "Formatted test post.",
                "hashtags": ["test"],
                "subreddit": None,
            }
        ),
    ]
    return MockLLMClient(responses)


@pytest.fixture()
def sample_brief():
    """Return a ContentBrief with realistic data."""
    return ContentBrief(
        topic="How to build a CLI in Python",
        angle="Focus on Typer + Rich for modern UX",
        target_audience="Python developers",
        relevant_links=["https://typer.tiangolo.com"],
        stream=ContentStream.project_marketing,
        platforms=[Platform.twitter, Platform.linkedin],
    )


@pytest.fixture()
def sample_post(sample_brief):
    """Return a PostDraft with realistic data (pending status, scheduled_time set)."""
    return PostDraft(
        brief_id=sample_brief.id,
        stream=ContentStream.project_marketing,
        platform=Platform.twitter,
        content="Build beautiful CLIs with Typer + Rich in Python.",
        hashtags=["python", "cli"],
        cta_url="https://typer.tiangolo.com",
        scheduled_time=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
    )


@pytest.fixture()
def sample_pipeline_run():
    """Return a PipelineRun with week_of=date(2025, 3, 3)."""
    return PipelineRun(week_of=date(2025, 3, 3))


@pytest.fixture()
def sample_config():
    """Return a dict with brand_voice, platform_rules, and schedule_rules sub-dicts."""
    return {
        "brand_voice": {
            "tone": "professional yet approachable",
            "vocabulary": ["innovative", "streamline", "empower"],
            "avoid": ["synergy", "disrupt"],
        },
        "platform_rules": {
            "twitter": {"max_chars": 280, "max_hashtags": 3},
            "linkedin": {"max_chars": 3000, "max_hashtags": 5},
            "reddit": {"max_chars": 10000, "require_subreddit": True},
        },
        "schedule_rules": {
            "posts_per_week": 10,
            "min_gap_hours": 4,
            "peak_hours": [9, 12, 17],
        },
    }

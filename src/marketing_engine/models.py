"""Pydantic v2 data models for marketing engine."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


class ContentBrief(BaseModel):
    """A content brief describing a single topic to write about."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    angle: str
    target_audience: str
    relevant_links: list[str] = []
    stream: ContentStream
    platforms: list[Platform]
    created_at: datetime = Field(default_factory=_utcnow)


class PostDraft(BaseModel):
    """A draft post for a specific platform."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    brief_id: str
    stream: ContentStream
    platform: Platform
    content: str
    media_urls: list[str] = []
    cta_url: str = ""
    hashtags: list[str] = []
    subreddit: str | None = None
    scheduled_time: datetime | None = None
    approval_status: ApprovalStatus = ApprovalStatus.pending
    edited_content: str | None = None
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PipelineRun(BaseModel):
    """Record of a single pipeline execution."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    week_of: date
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None
    briefs_count: int = 0
    drafts_count: int = 0
    posts_count: int = 0
    status: str = "running"
    error: str | None = None


class WeeklyQueue(BaseModel):
    """A week's worth of scheduled posts."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    week_of: date
    posts: list[PostDraft] = []
    created_at: datetime = Field(default_factory=_utcnow)

    def total_by_platform(self) -> dict[Platform, int]:
        """Count posts grouped by platform."""
        counts: dict[Platform, int] = {}
        for post in self.posts:
            counts[post.platform] = counts.get(post.platform, 0) + 1
        return counts

    def total_by_stream(self) -> dict[ContentStream, int]:
        """Count posts grouped by content stream."""
        counts: dict[ContentStream, int] = {}
        for post in self.posts:
            counts[post.stream] = counts.get(post.stream, 0) + 1
        return counts

    def pending_count(self) -> int:
        """Count posts with pending approval status."""
        return sum(1 for p in self.posts if p.approval_status == ApprovalStatus.pending)

    def approved_count(self) -> int:
        """Count posts with approved or edited status."""
        return sum(
            1
            for p in self.posts
            if p.approval_status in (ApprovalStatus.approved, ApprovalStatus.edited)
        )

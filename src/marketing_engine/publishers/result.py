"""Publish result model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from marketing_engine.enums import Platform


class PublishResult(BaseModel):
    """Result of a platform publish attempt."""

    success: bool
    platform: Platform
    post_id: str
    platform_post_id: str | None = None
    post_url: str | None = None
    error: str | None = None
    published_at: datetime | None = None

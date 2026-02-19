"""Enumeration types for marketing engine."""

from enum import StrEnum


class Platform(StrEnum):
    """Supported social media platforms."""

    twitter = "twitter"
    linkedin = "linkedin"
    reddit = "reddit"
    youtube = "youtube"
    tiktok = "tiktok"


class ContentStream(StrEnum):
    """Content stream categories."""

    project_marketing = "project_marketing"
    benchgoblins = "benchgoblins"
    eve_content = "eve_content"
    linux_tools = "linux_tools"
    technical_ai = "technical_ai"


class ApprovalStatus(StrEnum):
    """Post approval workflow statuses."""

    pending = "pending"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"

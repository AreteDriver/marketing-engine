"""Tests for marketing_engine.enums."""

import pytest

from marketing_engine.enums import ApprovalStatus, ContentStream, Platform


class TestPlatform:
    def test_members_count(self):
        assert len(Platform) == 5

    def test_member_values(self):
        assert Platform.twitter == "twitter"
        assert Platform.linkedin == "linkedin"
        assert Platform.reddit == "reddit"
        assert Platform.youtube == "youtube"
        assert Platform.tiktok == "tiktok"

    def test_str_equality(self):
        assert str(Platform.twitter) == "twitter"

    def test_construct_from_value(self):
        assert Platform("twitter") == Platform.twitter

    def test_iteration(self):
        names = [p.value for p in Platform]
        assert names == ["twitter", "linkedin", "reddit", "youtube", "tiktok"]


class TestContentStream:
    def test_members_count(self):
        assert len(ContentStream) == 5

    def test_member_values(self):
        assert ContentStream.project_marketing == "project_marketing"
        assert ContentStream.benchgoblins == "benchgoblins"
        assert ContentStream.eve_content == "eve_content"
        assert ContentStream.linux_tools == "linux_tools"
        assert ContentStream.technical_ai == "technical_ai"

    def test_str_equality(self):
        assert str(ContentStream.eve_content) == "eve_content"

    def test_construct_from_value(self):
        assert ContentStream("benchgoblins") == ContentStream.benchgoblins


class TestApprovalStatus:
    def test_members_count(self):
        assert len(ApprovalStatus) == 4

    def test_member_values(self):
        assert ApprovalStatus.pending == "pending"
        assert ApprovalStatus.approved == "approved"
        assert ApprovalStatus.edited == "edited"
        assert ApprovalStatus.rejected == "rejected"

    def test_str_equality(self):
        assert str(ApprovalStatus.approved) == "approved"

    def test_construct_from_value(self):
        assert ApprovalStatus("rejected") == ApprovalStatus.rejected


class TestInvalidValues:
    def test_invalid_platform_raises(self):
        with pytest.raises(ValueError):
            Platform("instagram")

    def test_invalid_stream_raises(self):
        with pytest.raises(ValueError):
            ContentStream("blog_posts")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            ApprovalStatus("cancelled")

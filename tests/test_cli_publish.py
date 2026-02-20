"""Tests for CLI publish commands: publish, publish-one, publish-status."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from marketing_engine.cli import app
from marketing_engine.db import reset_database
from marketing_engine.enums import Platform
from marketing_engine.exceptions import LicenseError, PublishError
from marketing_engine.publishers.result import PublishResult

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Point MKEN_DB_PATH at a temp file and clear the LRU cache before/after each test."""
    monkeypatch.setenv("MKEN_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MKEN_CONFIG_DIR", str(tmp_path / "configs"))
    monkeypatch.delenv("MKEN_LICENSE", raising=False)
    reset_database()
    yield
    reset_database()


def _make_success_result(
    platform: Platform = Platform.twitter,
    post_url: str = "https://example.com/post/1",
) -> PublishResult:
    return PublishResult(
        success=True,
        platform=platform,
        post_id="res-1",
        platform_post_id="plat-1",
        post_url=post_url,
        published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
    )


def _make_failure_result(
    platform: Platform = Platform.twitter,
    error: str = "API error",
) -> PublishResult:
    return PublishResult(
        success=False,
        platform=platform,
        post_id="res-fail",
        error=error,
    )


# ---------------------------------------------------------------------------
# publish command
# ---------------------------------------------------------------------------


class TestPublishDryRun:
    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_skips_license_check(self, mock_publish):
        mock_publish.return_value = []

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert result.exit_code == 0

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_no_posts_shows_message(self, mock_publish):
        mock_publish.return_value = []

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert result.exit_code == 0
        assert "No posts due" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_with_results_shows_published(self, mock_publish):
        mock_publish.return_value = [_make_success_result()]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert result.exit_code == 0
        assert "Published" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_with_failure_shows_failed(self, mock_publish):
        mock_publish.return_value = [_make_failure_result(error="timeout")]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert result.exit_code == 0
        assert "Failed" in result.output
        assert "timeout" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_shows_summary_counts(self, mock_publish):
        mock_publish.return_value = [
            _make_success_result(),
            _make_failure_result(),
        ]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert "1 published" in result.output
        assert "1 failed" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_dry_run_shows_post_url(self, mock_publish):
        mock_publish.return_value = [_make_success_result(post_url="https://twitter.com/status/42")]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert "https://twitter.com/status/42" in result.output


class TestPublishLicenseCheck:
    @patch("marketing_engine.licensing.require_feature", side_effect=LicenseError("PRO required"))
    def test_without_license_shows_error(self, _mock_feat):
        result = runner.invoke(app, ["publish"])

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    @patch("marketing_engine.licensing.require_feature")
    def test_with_license_proceeds(self, _mock_feat, mock_publish):
        mock_publish.return_value = []

        result = runner.invoke(app, ["publish"])

        assert result.exit_code == 0


class TestPublishInvalidPlatform:
    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_invalid_platform_shows_error(self, mock_publish):
        mock_publish.return_value = []

        result = runner.invoke(app, ["publish", "--dry-run", "--platform", "fakebook"])

        assert result.exit_code == 1
        assert "Invalid platform" in result.output


class TestPublishMixedResults:
    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_multiple_successes(self, mock_publish):
        mock_publish.return_value = [
            _make_success_result(platform=Platform.twitter),
            _make_success_result(platform=Platform.linkedin),
        ]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert "2 published" in result.output
        assert "0 failed" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_due_posts")
    def test_success_with_no_url(self, mock_publish):
        r = PublishResult(
            success=True,
            platform=Platform.twitter,
            post_id="no-url",
            published_at=datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
        )
        mock_publish.return_value = [r]

        result = runner.invoke(app, ["publish", "--dry-run"])

        assert "OK" in result.output


# ---------------------------------------------------------------------------
# publish-one command
# ---------------------------------------------------------------------------


class TestPublishOneDryRun:
    @patch("marketing_engine.publishers.scheduler.publish_single")
    def test_dry_run_skips_license(self, mock_single):
        mock_single.return_value = _make_success_result()

        result = runner.invoke(app, ["publish-one", "post-123", "--dry-run"])

        assert result.exit_code == 0

    @patch("marketing_engine.publishers.scheduler.publish_single")
    def test_shows_published_on_success(self, mock_single):
        mock_single.return_value = _make_success_result(post_url="https://twitter.com/post/42")

        result = runner.invoke(app, ["publish-one", "post-123", "--dry-run"])

        assert "Published" in result.output
        assert "https://twitter.com/post/42" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_single")
    def test_shows_failed_on_failure(self, mock_single):
        mock_single.return_value = _make_failure_result(error="auth failed")

        result = runner.invoke(app, ["publish-one", "post-123", "--dry-run"])

        assert "Failed" in result.output
        assert "auth failed" in result.output


class TestPublishOneLicenseCheck:
    @patch("marketing_engine.licensing.require_feature", side_effect=LicenseError("PRO required"))
    def test_without_license_shows_error(self, _mock_feat):
        result = runner.invoke(app, ["publish-one", "post-123"])

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("marketing_engine.publishers.scheduler.publish_single")
    @patch("marketing_engine.licensing.require_feature")
    def test_with_license_proceeds(self, _mock_feat, mock_single):
        mock_single.return_value = _make_success_result()

        result = runner.invoke(app, ["publish-one", "post-123"])

        assert result.exit_code == 0


class TestPublishOneErrors:
    @patch(
        "marketing_engine.publishers.scheduler.publish_single",
        side_effect=PublishError("Post not found: xyz"),
    )
    def test_not_found_shows_error(self, _mock_single):
        result = runner.invoke(app, ["publish-one", "xyz", "--dry-run"])

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch(
        "marketing_engine.publishers.scheduler.publish_single",
        side_effect=PublishError("Post xyz is not approved"),
    )
    def test_not_approved_shows_error(self, _mock_single):
        result = runner.invoke(app, ["publish-one", "xyz", "--dry-run"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestPublishOnePostIdPassed:
    @patch("marketing_engine.publishers.scheduler.publish_single")
    def test_passes_post_id_to_scheduler(self, mock_single):
        mock_single.return_value = _make_success_result()

        runner.invoke(app, ["publish-one", "my-post-id", "--dry-run"])

        # publish_single is called as publish_single(db, post_id, dry_run=...)
        call_args = mock_single.call_args
        assert call_args[0][1] == "my-post-id"


# ---------------------------------------------------------------------------
# publish-status command
# ---------------------------------------------------------------------------


class TestPublishStatusEmpty:
    def test_no_history_shows_message(self):
        result = runner.invoke(app, ["publish-status"])

        assert result.exit_code == 0
        assert "No publish history" in result.output


class TestPublishStatusWithData:
    @patch("marketing_engine.db.get_database")
    def test_shows_table_with_entries(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_publish_history.return_value = [
            {
                "post_id": "abc12345-long-id",
                "platform": "twitter",
                "status": "published",
                "post_url": "https://twitter.com/post/1",
                "published_at": "2025-03-04T14:00:00",
                "error": None,
            }
        ]
        mock_get_db.return_value = mock_db

        result = runner.invoke(app, ["publish-status"])

        assert result.exit_code == 0
        assert "twitter" in result.output
        assert "published" in result.output

    @patch("marketing_engine.db.get_database")
    def test_shows_failed_entries(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_publish_history.return_value = [
            {
                "post_id": "fail-post-12345678",
                "platform": "linkedin",
                "status": "failed",
                "post_url": None,
                "published_at": None,
                "error": "Auth error",
            }
        ]
        mock_get_db.return_value = mock_db

        result = runner.invoke(app, ["publish-status"])

        assert result.exit_code == 0
        assert "failed" in result.output

    @patch("marketing_engine.db.get_database")
    def test_respects_limit_option(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.get_publish_history.return_value = []
        mock_get_db.return_value = mock_db

        runner.invoke(app, ["publish-status", "--limit", "5"])

        mock_db.get_publish_history.assert_called_once_with(limit=5)

    @patch("marketing_engine.db.get_database")
    def test_truncates_long_post_ids(self, mock_get_db):
        mock_db = MagicMock()
        long_id = "abcdefgh-1234-5678-9012-ijklmnopqrst"
        mock_db.get_publish_history.return_value = [
            {
                "post_id": long_id,
                "platform": "twitter",
                "status": "published",
                "post_url": "",
                "published_at": "2025-03-04T14:00:00",
                "error": None,
            }
        ]
        mock_get_db.return_value = mock_db

        result = runner.invoke(app, ["publish-status"])

        assert result.exit_code == 0
        # Post ID is truncated to first 8 chars + "..."
        assert "abcdefgh..." in result.output

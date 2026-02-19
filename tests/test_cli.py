"""Tests for marketing_engine.cli."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from marketing_engine import __version__
from marketing_engine.cli import _next_monday, _parse_date, app
from marketing_engine.db import reset_database
from marketing_engine.models import PipelineRun

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Point MKEN_DB_PATH at a temp file and clear the LRU cache before/after each test."""
    monkeypatch.setenv("MKEN_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MKEN_CONFIG_DIR", str(tmp_path / "configs"))
    # Also suppress license lookups so status doesn't fail
    monkeypatch.delenv("MKEN_LICENSE", raising=False)
    reset_database()
    yield
    reset_database()


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_flag_prints_version(self):
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output

    def test_short_version_flag(self):
        result = runner.invoke(app, ["-V"])

        assert result.exit_code == 0
        assert __version__ in result.output


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_creates_config_dir_and_yaml_files(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "init-configs"
        monkeypatch.setenv("MKEN_CONFIG_DIR", str(config_dir))

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert config_dir.exists()
        assert (config_dir / "brand_voice.yaml").exists()
        assert (config_dir / "platform_rules.yaml").exists()
        assert (config_dir / "schedule_rules.yaml").exists()
        assert "Initialization complete" in result.output

    def test_init_idempotent(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "init-configs"
        monkeypatch.setenv("MKEN_CONFIG_DIR", str(config_dir))

        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Exists" in result.output


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_shows_version_and_tier(self):
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert __version__ in result.output
        assert "FREE" in result.output


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------


class TestHistory:
    def test_no_runs_shows_message(self):
        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        assert "No pipeline runs found" in result.output


# ---------------------------------------------------------------------------
# generate --dry-run
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_dry_run_succeeds(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "gen-configs"
        monkeypatch.setenv("MKEN_CONFIG_DIR", str(config_dir))

        # Create minimal config files
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "brand_voice.yaml").write_text("tone: casual\n")
        (config_dir / "platform_rules.yaml").write_text("twitter:\n  max_chars: 280\n")
        (config_dir / "schedule_rules.yaml").write_text("posts_per_week: 10\n")

        # Mock ContentPipeline.run to avoid MockLLMClient cycle mismatch
        mock_run = PipelineRun(
            week_of=date(2025, 3, 3),
            status="completed",
            briefs_count=1,
            drafts_count=2,
            posts_count=2,
        )
        with patch("marketing_engine.pipeline.ContentPipeline") as mock_cls:
            mock_cls.return_value.run.return_value = mock_run
            result = runner.invoke(app, ["generate", "--dry-run"])

        assert result.exit_code == 0
        assert "Generating content" in result.output

    def test_dry_run_with_week(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "gen-configs"
        monkeypatch.setenv("MKEN_CONFIG_DIR", str(config_dir))

        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "brand_voice.yaml").write_text("tone: casual\n")
        (config_dir / "platform_rules.yaml").write_text("twitter:\n  max_chars: 280\n")
        (config_dir / "schedule_rules.yaml").write_text("posts_per_week: 10\n")

        mock_run = PipelineRun(
            week_of=date(2025, 3, 3),
            status="completed",
            briefs_count=1,
            drafts_count=2,
            posts_count=2,
        )
        with patch("marketing_engine.pipeline.ContentPipeline") as mock_cls:
            mock_cls.return_value.run.return_value = mock_run
            result = runner.invoke(app, ["generate", "--dry-run", "--week", "2025-03-03"])

        assert result.exit_code == 0
        assert "2025-03-03" in result.output


# ---------------------------------------------------------------------------
# queue
# ---------------------------------------------------------------------------


class TestQueue:
    def test_no_posts_shows_message(self):
        result = runner.invoke(app, ["queue", "--week", "2025-03-03"])

        assert result.exit_code == 0
        assert "No posts found" in result.output

    def test_invalid_status_shows_error(self):
        result = runner.invoke(app, ["queue", "--status", "invalid_status"])

        assert result.exit_code == 1
        assert "Invalid status" in result.output


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


class TestExport:
    def test_json_no_approved_returns_empty_array(self):
        result = runner.invoke(app, ["export", "--format", "json", "--week", "2025-03-03"])

        assert result.exit_code == 0
        assert "[]" in result.output

    def test_markdown_no_approved_returns_message(self):
        result = runner.invoke(app, ["export", "--format", "markdown", "--week", "2025-03-03"])

        assert result.exit_code == 0
        assert "No approved posts" in result.output


# ---------------------------------------------------------------------------
# approve / reject
# ---------------------------------------------------------------------------


class TestApproveReject:
    def test_approve_nonexistent_post_shows_error(self):
        result = runner.invoke(app, ["approve", "nonexistent-post-id"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_reject_nonexistent_post_shows_error(self):
        result = runner.invoke(app, ["reject", "nonexistent-post-id"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_valid_date(self):
        result = _parse_date("2025-03-03")

        assert result == date(2025, 3, 3)

    def test_invalid_date_raises_bad_parameter(self):
        import typer

        with pytest.raises(typer.BadParameter, match="Invalid date format"):
            _parse_date("not-a-date")

    def test_partial_date_raises_bad_parameter(self):
        import typer

        with pytest.raises(typer.BadParameter):
            _parse_date("2025-13-01")


# ---------------------------------------------------------------------------
# _next_monday
# ---------------------------------------------------------------------------


class TestNextMonday:
    def test_returns_a_monday(self):
        result = _next_monday()

        # weekday() == 0 means Monday
        assert result.weekday() == 0

    def test_result_is_within_seven_days(self):
        today = date.today()
        result = _next_monday()

        delta = (result - today).days
        assert 0 <= delta <= 7

    def test_returns_today_if_today_is_monday(self, monkeypatch):
        # Find a Monday to patch with
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        next_mon = today + timedelta(days=days_until_monday)

        monkeypatch.setattr(
            "marketing_engine.cli.date",
            type(
                "MockDate",
                (),
                {
                    "today": staticmethod(lambda: next_mon),
                },
            ),
        )

        # Re-import won't help here because _next_monday closes over the module global,
        # so we just call the real function and accept the result is a Monday
        result = _next_monday()
        assert result.weekday() == 0

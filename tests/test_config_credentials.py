"""Tests for marketing_engine.config.get_platform_credentials."""

from __future__ import annotations

import pytest

from marketing_engine.config import get_platform_credentials
from marketing_engine.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Twitter
# ---------------------------------------------------------------------------


class TestTwitterCredentials:
    def test_returns_bearer_token_key(self, monkeypatch):
        monkeypatch.setenv("MKEN_TWITTER_BEARER_TOKEN", "tk-abc123")

        creds = get_platform_credentials("twitter")

        assert "bearer_token" in creds

    def test_reads_bearer_token_from_env(self, monkeypatch):
        monkeypatch.setenv("MKEN_TWITTER_BEARER_TOKEN", "tk-abc123")

        creds = get_platform_credentials("twitter")

        assert creds["bearer_token"] == "tk-abc123"

    def test_returns_empty_string_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("MKEN_TWITTER_BEARER_TOKEN", raising=False)

        creds = get_platform_credentials("twitter")

        assert creds["bearer_token"] == ""

    def test_returns_single_key(self, monkeypatch):
        monkeypatch.delenv("MKEN_TWITTER_BEARER_TOKEN", raising=False)

        creds = get_platform_credentials("twitter")

        assert len(creds) == 1


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------


class TestLinkedInCredentials:
    def test_returns_access_token_and_person_id(self, monkeypatch):
        monkeypatch.setenv("MKEN_LINKEDIN_ACCESS_TOKEN", "li-token")
        monkeypatch.setenv("MKEN_LINKEDIN_PERSON_ID", "li-person")

        creds = get_platform_credentials("linkedin")

        assert creds["access_token"] == "li-token"
        assert creds["person_id"] == "li-person"

    def test_has_two_keys(self, monkeypatch):
        monkeypatch.delenv("MKEN_LINKEDIN_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("MKEN_LINKEDIN_PERSON_ID", raising=False)

        creds = get_platform_credentials("linkedin")

        assert len(creds) == 2

    def test_missing_access_token_returns_empty(self, monkeypatch):
        monkeypatch.delenv("MKEN_LINKEDIN_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("MKEN_LINKEDIN_PERSON_ID", "person-1")

        creds = get_platform_credentials("linkedin")

        assert creds["access_token"] == ""
        assert creds["person_id"] == "person-1"

    def test_missing_person_id_returns_empty(self, monkeypatch):
        monkeypatch.setenv("MKEN_LINKEDIN_ACCESS_TOKEN", "token-1")
        monkeypatch.delenv("MKEN_LINKEDIN_PERSON_ID", raising=False)

        creds = get_platform_credentials("linkedin")

        assert creds["access_token"] == "token-1"
        assert creds["person_id"] == ""


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------


class TestRedditCredentials:
    def test_returns_all_four_keys(self, monkeypatch):
        monkeypatch.setenv("MKEN_REDDIT_CLIENT_ID", "rid")
        monkeypatch.setenv("MKEN_REDDIT_CLIENT_SECRET", "rsec")
        monkeypatch.setenv("MKEN_REDDIT_USERNAME", "ruser")
        monkeypatch.setenv("MKEN_REDDIT_PASSWORD", "rpass")

        creds = get_platform_credentials("reddit")

        assert creds["client_id"] == "rid"
        assert creds["client_secret"] == "rsec"
        assert creds["username"] == "ruser"
        assert creds["password"] == "rpass"

    def test_has_four_keys(self, monkeypatch):
        for var in (
            "MKEN_REDDIT_CLIENT_ID",
            "MKEN_REDDIT_CLIENT_SECRET",
            "MKEN_REDDIT_USERNAME",
            "MKEN_REDDIT_PASSWORD",
        ):
            monkeypatch.delenv(var, raising=False)

        creds = get_platform_credentials("reddit")

        assert len(creds) == 4

    def test_partial_env_returns_mix(self, monkeypatch):
        monkeypatch.setenv("MKEN_REDDIT_CLIENT_ID", "myid")
        monkeypatch.delenv("MKEN_REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("MKEN_REDDIT_USERNAME", raising=False)
        monkeypatch.delenv("MKEN_REDDIT_PASSWORD", raising=False)

        creds = get_platform_credentials("reddit")

        assert creds["client_id"] == "myid"
        assert creds["client_secret"] == ""
        assert creds["username"] == ""
        assert creds["password"] == ""


# ---------------------------------------------------------------------------
# Unknown platform
# ---------------------------------------------------------------------------


class TestUnknownPlatform:
    def test_raises_config_error(self):
        with pytest.raises(ConfigError, match="Unknown platform"):
            get_platform_credentials("tiktok")

    def test_error_includes_platform_name(self):
        with pytest.raises(ConfigError, match="mastodon"):
            get_platform_credentials("mastodon")

    def test_youtube_not_supported(self):
        with pytest.raises(ConfigError):
            get_platform_credentials("youtube")

    def test_empty_string_not_supported(self):
        with pytest.raises(ConfigError):
            get_platform_credentials("")


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("MKEN_TWITTER_BEARER_TOKEN", raising=False)

        creds = get_platform_credentials("twitter")

        assert isinstance(creds, dict)

    def test_all_values_are_strings(self, monkeypatch):
        monkeypatch.setenv("MKEN_TWITTER_BEARER_TOKEN", "token")

        creds = get_platform_credentials("twitter")

        for value in creds.values():
            assert isinstance(value, str)

    def test_all_keys_are_strings(self, monkeypatch):
        monkeypatch.delenv("MKEN_TWITTER_BEARER_TOKEN", raising=False)

        creds = get_platform_credentials("twitter")

        for key in creds:
            assert isinstance(key, str)

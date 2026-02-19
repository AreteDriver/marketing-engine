"""Tests for marketing_engine.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketing_engine.config import (
    _load_yaml,
    get_config_dir,
    get_db_path,
    get_llm_model,
    get_llm_provider,
    load_brand_voice,
    load_platform_rules,
    load_schedule_rules,
)
from marketing_engine.exceptions import ConfigError

# --- get_config_dir ---


class TestGetConfigDir:
    def test_default_is_configs(self, monkeypatch):
        monkeypatch.delenv("MKEN_CONFIG_DIR", raising=False)
        assert get_config_dir() == Path("configs")

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("MKEN_CONFIG_DIR", "/tmp/custom-configs")
        assert get_config_dir() == Path("/tmp/custom-configs")


# --- get_db_path ---


class TestGetDbPath:
    def test_default_path(self, monkeypatch):
        monkeypatch.delenv("MKEN_DB_PATH", raising=False)
        expected = Path.home() / ".local" / "share" / "marketing-engine" / "marketing.db"
        assert get_db_path() == expected

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("MKEN_DB_PATH", "/tmp/test.db")
        assert get_db_path() == Path("/tmp/test.db")


# --- get_llm_provider ---


class TestGetLLMProvider:
    def test_default_is_ollama(self, monkeypatch):
        monkeypatch.delenv("MKEN_LLM_PROVIDER", raising=False)
        assert get_llm_provider() == "ollama"

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("MKEN_LLM_PROVIDER", "anthropic")
        assert get_llm_provider() == "anthropic"


# --- get_llm_model ---


class TestGetLLMModel:
    def test_default_is_llama(self, monkeypatch):
        monkeypatch.delenv("MKEN_LLM_MODEL", raising=False)
        assert get_llm_model() == "llama3.2"

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("MKEN_LLM_MODEL", "claude-sonnet-4-20250514")
        assert get_llm_model() == "claude-sonnet-4-20250514"


# --- _load_yaml ---


class TestLoadYaml:
    def test_valid_yaml_dict(self, tmp_path):
        f = tmp_path / "good.yaml"
        f.write_text("key: value\nnested:\n  a: 1\n")
        result = _load_yaml(f)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            _load_yaml(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  - :\n  invalid: [unclosed")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            _load_yaml(f)

    def test_yaml_list_raises(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigError, match="Expected a mapping"):
            _load_yaml(f)


# --- load_brand_voice ---


class TestLoadBrandVoice:
    def test_loads_from_explicit_path(self, tmp_path):
        f = tmp_path / "voice.yaml"
        f.write_text("tone: professional\nvocabulary:\n  - build\n  - ship\n")
        result = load_brand_voice(f)
        assert result["tone"] == "professional"
        assert result["vocabulary"] == ["build", "ship"]

    def test_fallback_to_config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MKEN_CONFIG_DIR", str(tmp_path))
        bv = tmp_path / "brand_voice.yaml"
        bv.write_text("tone: casual\n")
        result = load_brand_voice()
        assert result == {"tone": "casual"}


# --- load_platform_rules ---


class TestLoadPlatformRules:
    def test_loads_from_explicit_path(self, tmp_path):
        f = tmp_path / "platforms.yaml"
        f.write_text("twitter:\n  max_chars: 280\n")
        result = load_platform_rules(f)
        assert result["twitter"]["max_chars"] == 280


# --- load_schedule_rules ---


class TestLoadScheduleRules:
    def test_loads_from_explicit_path(self, tmp_path):
        f = tmp_path / "schedule.yaml"
        f.write_text("posts_per_week: 14\nmin_gap_hours: 4\n")
        result = load_schedule_rules(f)
        assert result["posts_per_week"] == 14
        assert result["min_gap_hours"] == 4

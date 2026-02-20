"""Tests for timeless_clips.config — load_config and get_config_path."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from timeless_clips.config import _DEFAULTS, get_config_path, load_config


class TestLoadConfigNoFile:
    """load_config with no path returns defaults."""

    def test_returns_defaults_when_no_path(self) -> None:
        config = load_config()
        assert config["archive"]["base_url"] == "https://archive.org"
        assert config["llm"]["model"] == "llama3.2"
        assert config["tts"]["engine"] == "piper"
        assert config["output"]["resolution"] == "1080x1920"
        assert config["catalog"]["db_path"] == "catalog.db"

    def test_returns_all_default_sections(self) -> None:
        config = load_config()
        for section in _DEFAULTS:
            assert section in config

    def test_defaults_are_deep_copied(self) -> None:
        """Mutating returned config must not affect _DEFAULTS."""
        config = load_config()
        config["archive"]["base_url"] = "https://mutated.example.com"
        assert _DEFAULTS["archive"]["base_url"] == "https://archive.org"

    def test_none_path_returns_defaults(self) -> None:
        config = load_config(path=None)
        assert config["archive"]["base_url"] == "https://archive.org"

    def test_nonexistent_path_returns_defaults(self, tmp_path: Path) -> None:
        config = load_config(path=tmp_path / "nonexistent.yaml")
        assert config["llm"]["provider"] == "ollama"


class TestLoadConfigFromYAML:
    """load_config merges YAML file values with defaults."""

    def test_yaml_overrides_default_value(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"llm": {"model": "gpt-4o"}}))
        config = load_config(path=cfg_file)
        assert config["llm"]["model"] == "gpt-4o"
        # Other llm defaults preserved
        assert config["llm"]["provider"] == "ollama"
        assert config["llm"]["host"] == "http://localhost:11434"

    def test_yaml_adds_new_key_to_existing_section(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"llm": {"temperature": 0.7}}))
        config = load_config(path=cfg_file)
        assert config["llm"]["temperature"] == 0.7
        # Defaults still present
        assert config["llm"]["model"] == "llama3.2"

    def test_yaml_adds_new_section(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"custom": {"key": "value"}}))
        config = load_config(path=cfg_file)
        assert config["custom"] == {"key": "value"}
        # Defaults untouched
        assert "archive" in config

    def test_yaml_non_dict_section_value(self, tmp_path: Path) -> None:
        """A non-dict value for a section that exists as dict in defaults replaces it."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"tts": "disabled"}))
        config = load_config(path=cfg_file)
        assert config["tts"] == "disabled"

    def test_yaml_non_dict_new_section(self, tmp_path: Path) -> None:
        """A non-dict value for a brand new section is stored as-is."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"debug": True}))
        config = load_config(path=cfg_file)
        assert config["debug"] is True

    def test_empty_yaml_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("")
        config = load_config(path=cfg_file)
        # Empty file yields None from safe_load, fallback to {}
        assert config["archive"]["base_url"] == "https://archive.org"

    def test_multiple_sections_merged(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        user_cfg = {
            "llm": {"model": "claude-3"},
            "output": {"crf": 18, "max_duration": 45},
        }
        cfg_file.write_text(yaml.dump(user_cfg))
        config = load_config(path=cfg_file)
        assert config["llm"]["model"] == "claude-3"
        assert config["output"]["crf"] == 18
        assert config["output"]["max_duration"] == 45
        # Preserved defaults
        assert config["output"]["codec"] == "libx264"


class TestLoadConfigEnvVarOverrides:
    """Environment variable overrides take precedence over file and defaults."""

    def test_tc_cache_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_CACHE_DIR", "/tmp/test-cache")
        config = load_config()
        assert config["archive"]["cache_dir"] == "/tmp/test-cache"

    def test_tc_catalog_db(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_CATALOG_DB", "/tmp/test.db")
        config = load_config()
        assert config["catalog"]["db_path"] == "/tmp/test.db"

    def test_tc_output_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_OUTPUT_DIR", "/tmp/test-output")
        config = load_config()
        assert config["output"]["output_dir"] == "/tmp/test-output"

    def test_tc_llm_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_LLM_MODEL", "mixtral")
        config = load_config()
        assert config["llm"]["model"] == "mixtral"

    def test_env_overrides_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({"llm": {"model": "from-yaml"}}))
        monkeypatch.setenv("TC_LLM_MODEL", "from-env")
        config = load_config(path=cfg_file)
        assert config["llm"]["model"] == "from-env"

    def test_all_env_vars_at_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_CACHE_DIR", "/c")
        monkeypatch.setenv("TC_CATALOG_DB", "/d")
        monkeypatch.setenv("TC_OUTPUT_DIR", "/o")
        monkeypatch.setenv("TC_LLM_MODEL", "m")
        config = load_config()
        assert config["archive"]["cache_dir"] == "/c"
        assert config["catalog"]["db_path"] == "/d"
        assert config["output"]["output_dir"] == "/o"
        assert config["llm"]["model"] == "m"

    def test_unset_env_vars_leave_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TC_CACHE_DIR", raising=False)
        monkeypatch.delenv("TC_CATALOG_DB", raising=False)
        monkeypatch.delenv("TC_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("TC_LLM_MODEL", raising=False)
        config = load_config()
        assert config["archive"]["cache_dir"] == "cache/"
        assert config["catalog"]["db_path"] == "catalog.db"
        assert config["output"]["output_dir"] == "output/"
        assert config["llm"]["model"] == "llama3.2"


class TestGetConfigPath:
    """get_config_path default and env override."""

    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TC_CONFIG", raising=False)
        assert get_config_path() == Path("configs/config.yaml")

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TC_CONFIG", "/etc/timeless/custom.yaml")
        assert get_config_path() == Path("/etc/timeless/custom.yaml")

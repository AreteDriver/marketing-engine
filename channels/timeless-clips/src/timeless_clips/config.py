"""Configuration loading from YAML with env var overrides."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# Default config values
_DEFAULTS: dict = {
    "archive": {
        "base_url": "https://archive.org",
        "rate_limit_seconds": 1.0,
        "cache_dir": "cache/",
        "preferred_formats": ["mp4", "ogv", "avi"],
    },
    "llm": {
        "provider": "ollama",
        "model": "llama3.2",
        "host": "http://localhost:11434",
    },
    "tts": {
        "engine": "piper",
        "voice": "en_US-lessac-medium",
    },
    "captions": {
        "model": "base",
        "language": "en",
        "word_grouping": 3,
        "style": "white_outline",
    },
    "output": {
        "resolution": "1080x1920",
        "max_duration": 60,
        "format": "mp4",
        "codec": "libx264",
        "crf": 23,
        "output_dir": "output/",
    },
    "catalog": {
        "db_path": "catalog.db",
    },
}


def load_config(path: Path | None = None) -> dict:
    """Load config from YAML file, merging with defaults."""
    config = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULTS.items()}

    if path and path.exists():
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        for section, values in user.items():
            if isinstance(values, dict) and section in config:
                config[section] = {**config[section], **values}
            else:
                config[section] = values

    # Env var overrides
    if env_cache := os.environ.get("TC_CACHE_DIR"):
        config["archive"]["cache_dir"] = env_cache
    if env_db := os.environ.get("TC_CATALOG_DB"):
        config["catalog"]["db_path"] = env_db
    if env_out := os.environ.get("TC_OUTPUT_DIR"):
        config["output"]["output_dir"] = env_out
    if env_model := os.environ.get("TC_LLM_MODEL"):
        config["llm"]["model"] = env_model

    return config


def get_config_path() -> Path:
    """Return default config file path."""
    return Path(os.environ.get("TC_CONFIG", "configs/config.yaml"))

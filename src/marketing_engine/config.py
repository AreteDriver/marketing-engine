"""Configuration loading for marketing engine."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from marketing_engine.exceptions import ConfigError


def get_config_dir() -> Path:
    """Return the configuration directory path.

    Uses MKEN_CONFIG_DIR env var, falling back to ./configs/.
    """
    return Path(os.environ.get("MKEN_CONFIG_DIR", "configs"))


def get_db_path() -> Path:
    """Return the database file path.

    Uses MKEN_DB_PATH env var, falling back to
    ~/.local/share/marketing-engine/marketing.db.
    """
    default = Path.home() / ".local" / "share" / "marketing-engine" / "marketing.db"
    return Path(os.environ.get("MKEN_DB_PATH", str(default)))


def get_llm_provider() -> str:
    """Return the configured LLM provider name."""
    return os.environ.get("MKEN_LLM_PROVIDER", "ollama")


def get_llm_model() -> str:
    """Return the configured LLM model name."""
    return os.environ.get("MKEN_LLM_MODEL", "llama3.2")


def _load_yaml(path: Path) -> dict:
    """Load and parse a YAML file, raising ConfigError on failure."""
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Expected a mapping in {path}, got {type(data).__name__}")
    return data


_PLATFORM_CREDENTIALS: dict[str, dict[str, str]] = {
    "twitter": {
        "bearer_token": "MKEN_TWITTER_BEARER_TOKEN",
    },
    "linkedin": {
        "access_token": "MKEN_LINKEDIN_ACCESS_TOKEN",
        "person_id": "MKEN_LINKEDIN_PERSON_ID",
    },
    "reddit": {
        "client_id": "MKEN_REDDIT_CLIENT_ID",
        "client_secret": "MKEN_REDDIT_CLIENT_SECRET",
        "username": "MKEN_REDDIT_USERNAME",
        "password": "MKEN_REDDIT_PASSWORD",
    },
}


def get_platform_credentials(platform: str) -> dict[str, str]:
    """Load platform API credentials from environment variables.

    Args:
        platform: Platform name (twitter, linkedin, reddit).

    Returns:
        Dict mapping credential key to value.

    Raises:
        ConfigError: If the platform is not recognized.
    """
    env_map = _PLATFORM_CREDENTIALS.get(platform)
    if env_map is None:
        raise ConfigError(f"Unknown platform for credentials: {platform}")
    return {key: os.environ.get(env_var, "") for key, env_var in env_map.items()}


def load_brand_voice(path: Path | None = None) -> dict:
    """Load brand voice configuration.

    Args:
        path: Explicit path to brand_voice.yaml. If None, looks in config dir.

    Returns:
        Parsed brand voice configuration dict.

    Raises:
        ConfigError: If the file is missing or contains invalid YAML.
    """
    if path is None:
        path = get_config_dir() / "brand_voice.yaml"
    return _load_yaml(path)


def load_platform_rules(path: Path | None = None) -> dict:
    """Load platform-specific formatting rules.

    Args:
        path: Explicit path to platform_rules.yaml. If None, looks in config dir.

    Returns:
        Parsed platform rules configuration dict.

    Raises:
        ConfigError: If the file is missing or contains invalid YAML.
    """
    if path is None:
        path = get_config_dir() / "platform_rules.yaml"
    return _load_yaml(path)


def load_schedule_rules(path: Path | None = None) -> dict:
    """Load scheduling rules configuration.

    Args:
        path: Explicit path to schedule_rules.yaml. If None, looks in config dir.

    Returns:
        Parsed schedule rules configuration dict.

    Raises:
        ConfigError: If the file is missing or contains invalid YAML.
    """
    if path is None:
        path = get_config_dir() / "schedule_rules.yaml"
    return _load_yaml(path)

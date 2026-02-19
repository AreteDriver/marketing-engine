"""HMAC-based license key validation for marketing engine."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from marketing_engine.exceptions import LicenseError

_KEY_SALT = "marketing-engine-v1"
_KEY_PREFIX = "MKEN"
_ENV_LICENSE_KEY = "MKEN_LICENSE"
_CHECKSUM_LEN = 4

FREE_FEATURES = frozenset(
    {
        "generate",
        "review",
        "export",
        "status",
        "init",
        "queue",
        "history",
    }
)

PRO_FEATURES = frozenset(
    {
        "anthropic_llm",
        "openai_llm",
        "analytics",
        "multi_week",
        "custom_streams",
    }
)

_TIER_MAP = {
    "FREE": FREE_FEATURES,
    "PRO": FREE_FEATURES | PRO_FEATURES,
}

_LICENSE_FILE_LOCATIONS = [
    Path(".marketing-engine-license"),
    Path.home() / ".config" / "marketing-engine" / "license",
]


def _compute_checksum(body: str) -> str:
    """Compute a 4-character HMAC checksum for a key body."""
    digest = hmac.new(_KEY_SALT.encode(), body.encode(), hashlib.sha256).hexdigest()
    return digest[:_CHECKSUM_LEN].upper()


def generate_key(tier: str) -> str:
    """Generate a license key for the given tier.

    Args:
        tier: License tier — "FREE" or "PRO".

    Returns:
        A formatted license key string: MKEN-TIER-RANDOM-CHECKSUM.

    Raises:
        ValueError: If the tier is not recognized.
    """
    tier = tier.upper()
    if tier not in _TIER_MAP:
        raise ValueError(f"Unknown tier: {tier}. Must be one of: {list(_TIER_MAP)}")

    # Generate random segment
    random_segment = os.urandom(6).hex().upper()[:8]
    body = f"{_KEY_PREFIX}-{tier}-{random_segment}"
    checksum = _compute_checksum(body)
    return f"{body}-{checksum}"


def validate_key(key: str) -> tuple[bool, str]:
    """Validate a license key and return its tier.

    Args:
        key: The license key string to validate.

    Returns:
        A tuple of (is_valid, tier). If invalid, tier is "FREE".
    """
    if not key or not isinstance(key, str):
        return False, "FREE"

    key = key.strip()
    parts = key.split("-")

    # Expected format: MKEN-TIER-RANDOM-CHECKSUM (4 parts)
    if len(parts) != 4:
        return False, "FREE"

    prefix, tier, _random, checksum = parts

    if prefix != _KEY_PREFIX:
        return False, "FREE"

    tier = tier.upper()
    if tier not in _TIER_MAP:
        return False, "FREE"

    # Verify checksum
    body = f"{prefix}-{tier}-{_random}"
    expected = _compute_checksum(body)

    if not hmac.compare_digest(checksum.upper(), expected):
        return False, "FREE"

    return True, tier


def get_license() -> tuple[str | None, str]:
    """Find and validate the license key.

    Checks the environment variable first, then license file locations.

    Returns:
        A tuple of (key_or_none, tier). If no key found, returns (None, "FREE").
    """
    # Check environment variable
    env_key = os.environ.get(_ENV_LICENSE_KEY, "").strip()
    if env_key:
        valid, tier = validate_key(env_key)
        if valid:
            return env_key, tier

    # Check file locations
    for path in _LICENSE_FILE_LOCATIONS:
        if path.exists():
            try:
                file_key = path.read_text().strip()
            except OSError:
                continue
            if file_key:
                valid, tier = validate_key(file_key)
                if valid:
                    return file_key, tier

    return None, "FREE"


def has_feature(feature: str) -> bool:
    """Check if the current license allows a feature.

    Args:
        feature: Feature name to check.

    Returns:
        True if the feature is allowed.
    """
    _, tier = get_license()
    allowed = _TIER_MAP.get(tier, FREE_FEATURES)
    return feature in allowed


def require_feature(feature: str) -> None:
    """Raise LicenseError if the current license does not allow a feature.

    Args:
        feature: Feature name to require.

    Raises:
        LicenseError: If the feature is not allowed at the current tier.
    """
    if not has_feature(feature):
        _, tier = get_license()
        raise LicenseError(
            f"Feature '{feature}' requires a PRO license. "
            f"Current tier: {tier}. "
            f"Set {_ENV_LICENSE_KEY} or place a license file at "
            f"{_LICENSE_FILE_LOCATIONS[1]}"
        )

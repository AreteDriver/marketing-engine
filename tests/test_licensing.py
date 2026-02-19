"""Tests for marketing_engine.licensing."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from marketing_engine.exceptions import LicenseError
from marketing_engine.licensing import (
    _KEY_PREFIX,
    _KEY_SALT,
    FREE_FEATURES,
    PRO_FEATURES,
    generate_key,
    get_license,
    has_feature,
    require_feature,
    validate_key,
)

_KEY_PATTERN_FREE = re.compile(r"^MKEN-FREE-[A-F0-9]{8}-[A-F0-9]{4}$")
_KEY_PATTERN_PRO = re.compile(r"^MKEN-PRO-[A-F0-9]{8}-[A-F0-9]{4}$")

# Dummy file locations that don't exist, used when we need require_feature()
# to construct its error message (it accesses _LICENSE_FILE_LOCATIONS[1]).
_EMPTY_FILE_LOCATIONS: list[Path] = [Path("/dev/null"), Path("/dev/null")]


# --- generate_key ---


class TestGenerateKey:
    def test_free_key_format(self):
        key = generate_key("FREE")
        assert _KEY_PATTERN_FREE.match(key), f"Key {key!r} does not match FREE pattern"

    def test_pro_key_format(self):
        key = generate_key("PRO")
        assert _KEY_PATTERN_PRO.match(key), f"Key {key!r} does not match PRO pattern"

    def test_invalid_tier_raises(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            generate_key("INVALID")

    def test_case_insensitive(self):
        key = generate_key("free")
        assert _KEY_PATTERN_FREE.match(key)

    def test_generated_keys_are_unique(self):
        keys = {generate_key("FREE") for _ in range(10)}
        assert len(keys) == 10


# --- validate_key ---


class TestValidateKey:
    def test_valid_free_key(self):
        key = generate_key("FREE")
        valid, tier = validate_key(key)
        assert valid is True
        assert tier == "FREE"

    def test_valid_pro_key(self):
        key = generate_key("PRO")
        valid, tier = validate_key(key)
        assert valid is True
        assert tier == "PRO"

    def test_empty_string(self):
        valid, tier = validate_key("")
        assert valid is False
        assert tier == "FREE"

    def test_none_returns_false(self):
        valid, tier = validate_key(None)  # type: ignore[arg-type]
        assert valid is False
        assert tier == "FREE"

    def test_bad_format(self):
        valid, tier = validate_key("bad-format")
        assert valid is False
        assert tier == "FREE"

    def test_bad_checksum(self):
        valid, tier = validate_key("MKEN-FREE-12345678-ZZZZ")
        assert valid is False
        assert tier == "FREE"

    def test_wrong_prefix(self):
        valid, tier = validate_key("WRONG-FREE-12345678-XXXX")
        assert valid is False
        assert tier == "FREE"

    def test_whitespace_stripped(self):
        key = generate_key("PRO")
        valid, tier = validate_key(f"  {key}  ")
        assert valid is True
        assert tier == "PRO"


# --- get_license ---


class TestGetLicense:
    def test_no_env_no_file_returns_none_free(self, monkeypatch):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        key, tier = get_license()
        assert key is None
        assert tier == "FREE"

    def test_valid_env_var(self, monkeypatch):
        pro_key = generate_key("PRO")
        monkeypatch.setenv("MKEN_LICENSE", pro_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        key, tier = get_license()
        assert key == pro_key
        assert tier == "PRO"

    def test_invalid_env_var_falls_through(self, monkeypatch):
        monkeypatch.setenv("MKEN_LICENSE", "bad-key")
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        key, tier = get_license()
        assert key is None
        assert tier == "FREE"

    def test_valid_license_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        license_file = tmp_path / "license"
        pro_key = generate_key("PRO")
        license_file.write_text(pro_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [license_file])
        key, tier = get_license()
        assert key == pro_key
        assert tier == "PRO"

    def test_env_takes_precedence_over_file(self, monkeypatch, tmp_path):
        env_key = generate_key("FREE")
        file_key = generate_key("PRO")
        monkeypatch.setenv("MKEN_LICENSE", env_key)
        license_file = tmp_path / "license"
        license_file.write_text(file_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [license_file])
        key, tier = get_license()
        assert key == env_key
        assert tier == "FREE"


# --- has_feature ---


class TestHasFeature:
    def test_free_feature_no_license(self, monkeypatch):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        assert has_feature("generate") is True

    def test_pro_feature_no_license(self, monkeypatch):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        assert has_feature("anthropic_llm") is False

    def test_pro_feature_with_pro_license(self, monkeypatch):
        pro_key = generate_key("PRO")
        monkeypatch.setenv("MKEN_LICENSE", pro_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        assert has_feature("anthropic_llm") is True

    def test_free_feature_with_pro_license(self, monkeypatch):
        pro_key = generate_key("PRO")
        monkeypatch.setenv("MKEN_LICENSE", pro_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        assert has_feature("generate") is True


# --- require_feature ---


class TestRequireFeature:
    def test_free_feature_does_not_raise(self, monkeypatch):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        require_feature("generate")  # Should not raise

    def test_pro_feature_raises_without_license(self, monkeypatch):
        monkeypatch.delenv("MKEN_LICENSE", raising=False)
        # require_feature error message accesses _LICENSE_FILE_LOCATIONS[1],
        # so we need at least 2 entries in the mock list.
        monkeypatch.setattr(
            "marketing_engine.licensing._LICENSE_FILE_LOCATIONS", _EMPTY_FILE_LOCATIONS
        )
        with pytest.raises(LicenseError, match="requires a PRO license"):
            require_feature("anthropic_llm")

    def test_pro_feature_ok_with_pro_license(self, monkeypatch):
        pro_key = generate_key("PRO")
        monkeypatch.setenv("MKEN_LICENSE", pro_key)
        monkeypatch.setattr("marketing_engine.licensing._LICENSE_FILE_LOCATIONS", [])
        require_feature("anthropic_llm")  # Should not raise


# --- Feature sets ---


class TestFeatureSets:
    def test_free_features_is_frozenset(self):
        assert isinstance(FREE_FEATURES, frozenset)

    def test_pro_features_is_frozenset(self):
        assert isinstance(PRO_FEATURES, frozenset)

    def test_free_features_contents(self):
        expected = {"generate", "review", "export", "status", "init", "queue", "history"}
        assert expected == FREE_FEATURES

    def test_pro_features_contents(self):
        expected = {"anthropic_llm", "openai_llm", "analytics", "multi_week", "custom_streams"}
        assert expected == PRO_FEATURES

    def test_no_overlap_between_tiers(self):
        assert FREE_FEATURES.isdisjoint(PRO_FEATURES)


# --- Constants ---


class TestConstants:
    def test_key_prefix(self):
        assert _KEY_PREFIX == "MKEN"

    def test_key_salt(self):
        assert _KEY_SALT == "marketing-engine-v1"

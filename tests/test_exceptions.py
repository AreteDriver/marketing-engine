"""Tests for marketing_engine.exceptions."""

import pytest

from marketing_engine.exceptions import (
    ConfigError,
    DatabaseError,
    LicenseError,
    LLMError,
    MarketingEngineError,
    PipelineError,
)

ALL_EXCEPTIONS = [ConfigError, DatabaseError, LLMError, PipelineError, LicenseError]


class TestMarketingEngineError:
    def test_inherits_from_exception(self):
        assert issubclass(MarketingEngineError, Exception)

    def test_preserves_message(self):
        err = MarketingEngineError("base error")
        assert str(err) == "base error"


class TestChildExceptions:
    @pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
    def test_inherits_from_base(self, exc_cls):
        assert issubclass(exc_cls, MarketingEngineError)

    @pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
    def test_can_raise_and_catch_by_parent(self, exc_cls):
        with pytest.raises(MarketingEngineError):
            raise exc_cls("test message")

    @pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
    def test_preserves_message(self, exc_cls):
        err = exc_cls("specific error")
        assert str(err) == "specific error"

    @pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
    def test_inherits_from_exception(self, exc_cls):
        assert issubclass(exc_cls, Exception)

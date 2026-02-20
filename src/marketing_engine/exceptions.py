"""Exception hierarchy for marketing engine."""


class MarketingEngineError(Exception):
    """Base exception for all marketing engine errors."""


class ConfigError(MarketingEngineError):
    """Configuration loading or validation error."""


class LLMError(MarketingEngineError):
    """LLM generation or communication error."""


class DatabaseError(MarketingEngineError):
    """Database operation error."""


class PipelineError(MarketingEngineError):
    """Content pipeline execution error."""


class LicenseError(MarketingEngineError):
    """License validation or feature access error."""


class PublishError(MarketingEngineError):
    """Platform publishing error."""

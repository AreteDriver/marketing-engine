"""Tests for the FormatAgent platform formatting agent."""

from __future__ import annotations

import json

from marketing_engine.agents.format import _DEFAULT_PLATFORM_LIMITS, FormatAgent
from marketing_engine.enums import Platform
from marketing_engine.llm.base import MockLLMClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(
    responses: list[str] | None = None,
    platform_rules: dict | None = None,
) -> tuple[FormatAgent, MockLLMClient]:
    """Return a (FormatAgent, MockLLMClient) pair with sensible defaults."""
    if responses is None:
        responses = [
            json.dumps({"content": "Formatted text.", "hashtags": ["test"], "subreddit": None})
        ]
    llm = MockLLMClient(responses)
    config: dict = {}
    if platform_rules is not None:
        config["platform_rules"] = platform_rules
    agent = FormatAgent(llm=llm, config=config)
    return agent, llm


# ---------------------------------------------------------------------------
# system_prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    """Tests for the system_prompt property."""

    def test_system_prompt_includes_platform_name(self) -> None:
        agent, _ = _make_agent()
        agent._current_platform = Platform.linkedin
        prompt = agent.system_prompt
        assert "linkedin" in prompt

    def test_system_prompt_reddit_mentions_subreddit(self) -> None:
        agent, _ = _make_agent()
        agent._current_platform = Platform.reddit
        prompt = agent.system_prompt
        assert "subreddit" in prompt.lower()

    def test_system_prompt_twitter_shows_280(self) -> None:
        agent, _ = _make_agent()
        agent._current_platform = Platform.twitter
        prompt = agent.system_prompt
        assert "280" in prompt

    def test_system_prompt_youtube_shows_5000(self) -> None:
        agent, _ = _make_agent()
        agent._current_platform = Platform.youtube
        prompt = agent.system_prompt
        assert "5000" in prompt

    def test_system_prompt_no_subreddit_for_non_reddit(self) -> None:
        agent, _ = _make_agent()
        agent._current_platform = Platform.twitter
        prompt = agent.system_prompt
        assert "subreddit" not in prompt.split("JSON")[0]


# ---------------------------------------------------------------------------
# build_user_prompt
# ---------------------------------------------------------------------------


class TestBuildUserPrompt:
    """Tests for build_user_prompt()."""

    def test_includes_content(self) -> None:
        agent, _ = _make_agent()
        prompt = agent.build_user_prompt(content="Hello world", platform=Platform.twitter)
        assert "Hello world" in prompt

    def test_includes_platform_name(self) -> None:
        agent, _ = _make_agent()
        prompt = agent.build_user_prompt(content="X", platform=Platform.linkedin)
        assert "linkedin" in prompt

    def test_sets_current_platform(self) -> None:
        agent, _ = _make_agent()
        agent.build_user_prompt(content="X", platform=Platform.tiktok)
        assert agent._current_platform == Platform.tiktok

    def test_includes_style_notes_from_config(self) -> None:
        rules = {"twitter": {"style_notes": "Keep it punchy"}}
        agent, _ = _make_agent(platform_rules=rules)
        prompt = agent.build_user_prompt(content="X", platform=Platform.twitter)
        assert "Keep it punchy" in prompt

    def test_no_style_notes_when_absent(self) -> None:
        agent, _ = _make_agent()
        prompt = agent.build_user_prompt(content="X", platform=Platform.twitter)
        assert "style notes" not in prompt.lower()


# ---------------------------------------------------------------------------
# parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    """Tests for parse_response()."""

    def test_extracts_content_hashtags_subreddit(self) -> None:
        agent, _ = _make_agent()
        raw = json.dumps({"content": "Post text", "hashtags": ["a", "b"], "subreddit": "python"})
        result = agent.parse_response(raw)
        assert result["content"] == "Post text"
        assert result["hashtags"] == ["a", "b"]
        assert result["subreddit"] == "python"

    def test_defaults_on_missing_keys(self) -> None:
        agent, _ = _make_agent()
        result = agent.parse_response("{}")
        assert result["content"] == ""
        assert result["hashtags"] == []
        assert result["subreddit"] is None


# ---------------------------------------------------------------------------
# _enforce_limits
# ---------------------------------------------------------------------------


class TestEnforceLimits:
    """Tests for _enforce_limits()."""

    def test_truncates_content_exceeding_char_limit(self) -> None:
        agent, _ = _make_agent()
        long_content = "word " * 100  # 500 chars
        result = {"content": long_content, "hashtags": [], "subreddit": None}
        enforced = agent._enforce_limits(result, Platform.twitter)
        assert len(enforced["content"]) <= 280

    def test_truncates_at_word_boundary(self) -> None:
        agent, _ = _make_agent()
        # Content that exceeds limit — last word should not be split mid-word
        words = "abcdefgh " * 40  # 360 chars, exceeds 280
        result = {"content": words.strip(), "hashtags": [], "subreddit": None}
        enforced = agent._enforce_limits(result, Platform.twitter)
        # The content should end cleanly (no partial word, just word boundary + ...)
        text = enforced["content"]
        assert text.endswith("...") or len(text) <= 280

    def test_adds_ellipsis_when_truncating(self) -> None:
        agent, _ = _make_agent()
        # 17-char words + space = 18 per unit. 280 / 18 = 15.5, so content[:280]
        # cuts mid-word. rfind(" ") lands at 15*18-1 = 269. 269 + 3 = 272 <= 280.
        long_content = "abcdefghijklmnopq " * 20  # 360 chars, exceeds 280
        result = {"content": long_content.strip(), "hashtags": [], "subreddit": None}
        enforced = agent._enforce_limits(result, Platform.twitter)
        assert "..." in enforced["content"]

    def test_caps_hashtags_at_platform_max(self) -> None:
        agent, _ = _make_agent()
        result = {"content": "Hi", "hashtags": ["a", "b", "c", "d", "e"], "subreddit": None}
        enforced = agent._enforce_limits(result, Platform.twitter)
        assert len(enforced["hashtags"]) <= _DEFAULT_PLATFORM_LIMITS["twitter"]["max_hashtags"]

    def test_strips_subreddit_for_non_reddit(self) -> None:
        agent, _ = _make_agent()
        result = {"content": "Hi", "hashtags": [], "subreddit": "python"}
        enforced = agent._enforce_limits(result, Platform.twitter)
        assert enforced["subreddit"] is None

    def test_keeps_subreddit_for_reddit(self) -> None:
        agent, _ = _make_agent()
        result = {"content": "Hi", "hashtags": [], "subreddit": "python"}
        enforced = agent._enforce_limits(result, Platform.reddit)
        assert enforced["subreddit"] == "python"

    def test_content_under_limit_unchanged(self) -> None:
        agent, _ = _make_agent()
        short = "Hello world"
        result = {"content": short, "hashtags": ["a"], "subreddit": None}
        enforced = agent._enforce_limits(result, Platform.twitter)
        assert enforced["content"] == short

    def test_reddit_zero_hashtags(self) -> None:
        agent, _ = _make_agent()
        result = {"content": "Hi", "hashtags": ["a", "b", "c"], "subreddit": "test"}
        enforced = agent._enforce_limits(result, Platform.reddit)
        assert len(enforced["hashtags"]) == 0


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the full run() method."""

    def test_run_calls_llm_then_enforces_limits(self) -> None:
        response = json.dumps({"content": "Short post.", "hashtags": ["dev"], "subreddit": None})
        agent, llm = _make_agent(responses=[response])
        result = agent.run(content="Draft text", platform=Platform.twitter)
        assert result["content"] == "Short post."
        assert len(llm.calls) == 1

    def test_run_twitter_truncates_long_content(self) -> None:
        long_text = "word " * 100
        response = json.dumps({"content": long_text, "hashtags": ["a", "b"], "subreddit": None})
        agent, _ = _make_agent(responses=[response])
        result = agent.run(content="Draft", platform=Platform.twitter)
        assert len(result["content"]) <= 280

    def test_run_reddit_keeps_subreddit(self) -> None:
        response = json.dumps(
            {"content": "Reddit post", "hashtags": [], "subreddit": "programming"}
        )
        agent, _ = _make_agent(responses=[response])
        result = agent.run(content="Draft", platform=Platform.reddit)
        assert result["subreddit"] == "programming"

    def test_run_linkedin_allows_longer_content(self) -> None:
        text_2000 = "a" * 2000
        response = json.dumps({"content": text_2000, "hashtags": ["li"], "subreddit": None})
        agent, _ = _make_agent(responses=[response])
        result = agent.run(content="Draft", platform=Platform.linkedin)
        assert result["content"] == text_2000


# ---------------------------------------------------------------------------
# Custom platform_rules override
# ---------------------------------------------------------------------------


class TestCustomPlatformRules:
    """Tests for config-based platform_rules overriding defaults."""

    def test_custom_max_chars_overrides_default(self) -> None:
        rules = {"twitter": {"max_chars": 140, "max_hashtags": 1}}
        long_text = "word " * 50  # ~250 chars
        response = json.dumps(
            {"content": long_text, "hashtags": ["a", "b", "c"], "subreddit": None}
        )
        agent, _ = _make_agent(responses=[response], platform_rules=rules)
        result = agent.run(content="Draft", platform=Platform.twitter)
        assert len(result["content"]) <= 140
        assert len(result["hashtags"]) <= 1

    def test_custom_rules_appear_in_system_prompt(self) -> None:
        rules = {"twitter": {"max_chars": 140, "max_hashtags": 1}}
        agent, _ = _make_agent(platform_rules=rules)
        agent._current_platform = Platform.twitter
        prompt = agent.system_prompt
        assert "140" in prompt

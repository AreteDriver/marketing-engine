"""Tests for marketing_engine.agents.draft."""

import json

import pytest

from marketing_engine.agents.draft import DraftAgent
from marketing_engine.enums import ContentStream, Platform
from marketing_engine.llm.base import MockLLMClient
from marketing_engine.models import ContentBrief


@pytest.fixture()
def draft_brief() -> ContentBrief:
    """A ContentBrief for draft agent testing."""
    return ContentBrief(
        topic="Building CLIs with Typer",
        angle="Focus on Rich integration for beautiful output",
        target_audience="Python developers",
        relevant_links=["https://typer.tiangolo.com", "https://rich.readthedocs.io"],
        stream=ContentStream.project_marketing,
        platforms=[Platform.twitter, Platform.linkedin],
    )


def _canned_draft(**overrides) -> str:
    """Return canned JSON for a draft response."""
    base = {
        "content": "Test post content here.",
        "cta_url": "https://example.com",
        "hashtags": ["python", "cli"],
    }
    base.update(overrides)
    return json.dumps(base)


class TestSystemPrompt:
    def test_contains_default_avoid_phrases(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.system_prompt
        for phrase in ["excited to announce", "game-changer", "leveraging AI", "synergy"]:
            assert phrase in prompt

    def test_uses_custom_avoid_list(self):
        config = {"brand_voice": {"avoid": ["buzzword", "paradigm shift"]}}
        agent = DraftAgent(MockLLMClient(["x"]), config)
        prompt = agent.system_prompt
        assert "buzzword" in prompt
        assert "paradigm shift" in prompt
        # Default phrases should not appear
        assert "synergy" not in prompt

    def test_uses_custom_principles(self):
        config = {"brand_voice": {"principles": ["Be concise", "Use data"]}}
        agent = DraftAgent(MockLLMClient(["x"]), config)
        prompt = agent.system_prompt
        assert "Be concise" in prompt
        assert "Use data" in prompt

    def test_contains_default_principles(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.system_prompt
        assert "Be direct and specific" in prompt
        assert "Show results, not promises" in prompt

    def test_contains_json_output_instruction(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.system_prompt
        assert "JSON" in prompt
        assert "content" in prompt


class TestBuildUserPrompt:
    def test_with_brief_includes_topic(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "Building CLIs with Typer" in prompt

    def test_with_brief_includes_angle(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "Rich integration" in prompt

    def test_with_brief_includes_audience(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "Python developers" in prompt

    def test_with_brief_includes_stream(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "project_marketing" in prompt

    def test_with_brief_includes_platforms(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "twitter" in prompt
        assert "linkedin" in prompt

    def test_with_none_brief_returns_generic(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=None)
        assert "general developer marketing post" in prompt.lower()

    def test_includes_stream_tone(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        # project_marketing tone should be present
        assert "Professional but approachable" in prompt

    def test_includes_relevant_links(self, draft_brief):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=draft_brief)
        assert "https://typer.tiangolo.com" in prompt
        assert "https://rich.readthedocs.io" in prompt

    def test_no_links_shows_none(self):
        brief = ContentBrief(
            topic="Test",
            angle="angle",
            target_audience="devs",
            relevant_links=[],
            stream=ContentStream.technical_ai,
            platforms=[Platform.twitter],
        )
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=brief)
        assert "none" in prompt

    def test_eve_content_stream_tone(self):
        brief = ContentBrief(
            topic="Wormhole mapping",
            angle="Exploration focus",
            target_audience="capsuleers",
            relevant_links=[],
            stream=ContentStream.eve_content,
            platforms=[Platform.reddit],
        )
        agent = DraftAgent(MockLLMClient(["x"]), {})
        prompt = agent.build_user_prompt(brief=brief)
        assert "capsuleers" in prompt  # from the stream tone


class TestParseResponse:
    def test_extracts_content_cta_hashtags(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        raw = json.dumps({"content": "Hello world", "cta_url": "https://x.com", "hashtags": ["a"]})
        result = agent.parse_response(raw)
        assert result["content"] == "Hello world"
        assert result["cta_url"] == "https://x.com"
        assert result["hashtags"] == ["a"]

    def test_missing_keys_default_to_empty(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        raw = json.dumps({})
        result = agent.parse_response(raw)
        assert result["content"] == ""
        assert result["cta_url"] == ""
        assert result["hashtags"] == []

    def test_invalid_json_raises_decode_error(self):
        agent = DraftAgent(MockLLMClient(["x"]), {})
        with pytest.raises(json.JSONDecodeError):
            agent.parse_response("not json {")


class TestRunEndToEnd:
    def test_returns_dict_with_expected_keys(self, draft_brief):
        llm = MockLLMClient([_canned_draft()])
        agent = DraftAgent(llm, {})
        result = agent.run(brief=draft_brief)
        assert "content" in result
        assert "cta_url" in result
        assert "hashtags" in result

    def test_passes_brief_through_kwargs(self, draft_brief):
        llm = MockLLMClient([_canned_draft()])
        agent = DraftAgent(llm, {})
        agent.run(brief=draft_brief)
        # Verify the prompt included brief data
        _, user_prompt = llm.calls[0]
        assert draft_brief.topic in user_prompt

    def test_invalid_json_triggers_retry(self, draft_brief):
        llm = MockLLMClient(["not json", _canned_draft()])
        agent = DraftAgent(llm, {})
        result = agent.run(brief=draft_brief)
        assert result["content"] == "Test post content here."
        assert len(llm.calls) == 2

    def test_run_without_brief_uses_generic_prompt(self):
        llm = MockLLMClient([_canned_draft()])
        agent = DraftAgent(llm, {})
        result = agent.run()
        _, user_prompt = llm.calls[0]
        assert "general developer marketing post" in user_prompt.lower()
        assert result["content"] == "Test post content here."

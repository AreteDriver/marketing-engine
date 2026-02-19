"""Tests for marketing_engine.agents.research."""

import json

import pytest

from marketing_engine.agents.research import ResearchAgent
from marketing_engine.enums import ContentStream, Platform
from marketing_engine.llm.base import MockLLMClient
from marketing_engine.models import ContentBrief


def _brief_json(**overrides) -> dict:
    """Build a valid brief dict with sensible defaults, applying overrides."""
    base = {
        "topic": "Test Topic",
        "angle": "Test angle",
        "target_audience": "developers",
        "relevant_links": ["https://example.com"],
        "stream": "project_marketing",
        "platforms": ["twitter", "linkedin"],
    }
    base.update(overrides)
    return base


class TestSystemPrompt:
    def test_contains_content_strategist(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        assert "content strategist" in agent.system_prompt

    def test_contains_json_array(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        assert "JSON array" in agent.system_prompt

    def test_lists_expected_fields(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        for field in ("topic", "angle", "target_audience", "relevant_links", "stream", "platforms"):
            assert field in agent.system_prompt


class TestBuildUserPrompt:
    def test_no_streams_lists_all_defaults(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        prompt = agent.build_user_prompt()
        for stream in ContentStream:
            assert stream.value in prompt

    def test_specific_streams_only_those(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        prompt = agent.build_user_prompt(streams=["eve_content", "benchgoblins"])
        assert "eve_content" in prompt
        assert "benchgoblins" in prompt
        assert "linux_tools" not in prompt

    def test_with_activity_includes_activity_text(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        prompt = agent.build_user_prompt(activity="Shipped v2.0 today")
        assert "Shipped v2.0 today" in prompt
        assert "Recent activity" in prompt

    def test_without_activity_omits_activity_section(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        prompt = agent.build_user_prompt()
        assert "Recent activity" not in prompt

    def test_prompt_includes_brief_count_instruction(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        prompt = agent.build_user_prompt()
        assert "one brief per stream" in prompt.lower()


class TestParseResponse:
    def test_valid_json_array_returns_content_briefs(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps([_brief_json()])
        result = agent.parse_response(raw)
        assert len(result) == 1
        assert isinstance(result[0], ContentBrief)
        assert result[0].topic == "Test Topic"

    def test_single_json_object_wrapped_in_list(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps(_brief_json())
        result = agent.parse_response(raw)
        assert len(result) == 1
        assert isinstance(result[0], ContentBrief)

    def test_normalizes_unknown_platform_to_twitter(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps([_brief_json(platforms=["fakebook"])])
        result = agent.parse_response(raw)
        assert result[0].platforms == [Platform.twitter]

    def test_normalizes_unknown_stream_to_project_marketing(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps([_brief_json(stream="nonexistent_stream")])
        result = agent.parse_response(raw)
        assert result[0].stream == ContentStream.project_marketing

    def test_handles_missing_fields_with_defaults(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps([{}])
        result = agent.parse_response(raw)
        assert result[0].topic == "Untitled"
        assert result[0].angle == ""
        assert result[0].target_audience == "developers"
        assert result[0].relevant_links == []
        assert result[0].stream == ContentStream.project_marketing
        assert result[0].platforms == [Platform.twitter]

    def test_preserves_valid_platforms(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        raw = json.dumps([_brief_json(platforms=["twitter", "reddit", "linkedin"])])
        result = agent.parse_response(raw)
        assert set(result[0].platforms) == {Platform.twitter, Platform.reddit, Platform.linkedin}

    def test_multiple_briefs_parsed(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        briefs = [
            _brief_json(topic="Topic 1", stream="eve_content"),
            _brief_json(topic="Topic 2", stream="benchgoblins"),
        ]
        result = agent.parse_response(json.dumps(briefs))
        assert len(result) == 2
        assert result[0].topic == "Topic 1"
        assert result[1].topic == "Topic 2"

    def test_invalid_json_raises_json_decode_error(self):
        agent = ResearchAgent(MockLLMClient(["[]"]), {})
        with pytest.raises(json.JSONDecodeError):
            agent.parse_response("not json")


class TestRunEndToEnd:
    def test_returns_list_of_briefs(self):
        canned = json.dumps([_brief_json()])
        llm = MockLLMClient([canned])
        agent = ResearchAgent(llm, {})
        result = agent.run()
        assert len(result) == 1
        assert isinstance(result[0], ContentBrief)

    def test_with_streams_passes_through(self):
        canned = json.dumps([_brief_json(stream="eve_content")])
        llm = MockLLMClient([canned])
        agent = ResearchAgent(llm, {})
        result = agent.run(streams=["eve_content"])
        assert len(result) == 1
        # Verify the prompt used the specific stream
        _, user_prompt = llm.calls[0]
        assert "eve_content" in user_prompt

    def test_invalid_json_triggers_retry(self):
        canned_good = json.dumps([_brief_json()])
        llm = MockLLMClient(["not json", canned_good])
        agent = ResearchAgent(llm, {})
        result = agent.run()
        assert len(result) == 1
        assert len(llm.calls) == 2

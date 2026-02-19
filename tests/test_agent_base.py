"""Tests for marketing_engine.agents.base."""

import json

import pytest

from marketing_engine.agents.base import BaseAgent
from marketing_engine.exceptions import LLMError
from marketing_engine.llm.base import MockLLMClient


class _TestAgent(BaseAgent):
    """Concrete subclass for testing BaseAgent."""

    @property
    def system_prompt(self) -> str:
        return "test system prompt"

    def build_user_prompt(self, **kwargs) -> str:
        return f"test: {kwargs}"

    def parse_response(self, raw: str):
        return json.loads(raw)


class TestBaseAgentAbstract:
    def test_cannot_instantiate_directly(self):
        llm = MockLLMClient(["x"])
        with pytest.raises(TypeError, match="abstract method"):
            BaseAgent(llm, {})

    def test_has_all_abstract_methods(self):
        expected = {"system_prompt", "build_user_prompt", "parse_response"}
        assert BaseAgent.__abstractmethods__ == expected


class TestStripJsonFences:
    def _make_agent(self):
        return _TestAgent(MockLLMClient(["x"]), {})

    def test_removes_json_fences(self):
        agent = self._make_agent()
        raw = '```json\n{"key": "value"}\n```'
        assert agent._strip_json_fences(raw) == '{"key": "value"}'

    def test_removes_plain_fences(self):
        agent = self._make_agent()
        raw = '```\n{"key": "value"}\n```'
        assert agent._strip_json_fences(raw) == '{"key": "value"}'

    def test_leaves_clean_json_untouched(self):
        agent = self._make_agent()
        raw = '{"key": "value"}'
        assert agent._strip_json_fences(raw) == '{"key": "value"}'

    def test_handles_extra_whitespace(self):
        agent = self._make_agent()
        raw = '  ```json\n  {"key": "value"}  \n```  '
        result = agent._strip_json_fences(raw)
        assert json.loads(result) == {"key": "value"}

    def test_handles_no_newline_after_fence(self):
        agent = self._make_agent()
        raw = '```json{"key": 1}```'
        result = agent._strip_json_fences(raw)
        assert json.loads(result) == {"key": 1}


class TestRunMethod:
    def test_calls_llm_with_correct_prompts(self):
        llm = MockLLMClient(['{"result": true}'])
        agent = _TestAgent(llm, {})
        agent.run(foo="bar")
        assert len(llm.calls) == 1
        system, user = llm.calls[0]
        assert system == "test system prompt"
        assert "foo" in user
        assert "bar" in user

    def test_returns_parsed_json(self):
        llm = MockLLMClient(['{"answer": 42}'])
        agent = _TestAgent(llm, {})
        result = agent.run()
        assert result == {"answer": 42}

    def test_retries_on_json_parse_failure_then_succeeds(self):
        llm = MockLLMClient(["not json", '{"ok": true}'])
        agent = _TestAgent(llm, {})
        result = agent.run()
        assert result == {"ok": True}
        assert len(llm.calls) == 2

    def test_raises_llm_error_after_both_attempts_fail(self):
        llm = MockLLMClient(["bad json", "still bad"])
        agent = _TestAgent(llm, {})
        with pytest.raises(LLMError, match="Failed to parse"):
            agent.run()
        assert len(llm.calls) == 2

    def test_strips_fences_before_parsing(self):
        llm = MockLLMClient(['```json\n{"fenced": true}\n```'])
        agent = _TestAgent(llm, {})
        result = agent.run()
        assert result == {"fenced": True}

    def test_retry_prompt_includes_correction(self):
        llm = MockLLMClient(["not json", '{"ok": true}'])
        agent = _TestAgent(llm, {})
        agent.run()
        # Second call should include correction text
        _, retry_prompt = llm.calls[1]
        assert "not valid JSON" in retry_prompt

    def test_passes_kwargs_to_build_user_prompt(self):
        llm = MockLLMClient(['{"r": 1}'])
        agent = _TestAgent(llm, {})
        agent.run(alpha="one", beta="two")
        _, user = llm.calls[0]
        assert "alpha" in user
        assert "beta" in user

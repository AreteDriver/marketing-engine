"""Tests for marketing_engine.llm.base."""

import pytest

from marketing_engine.llm.base import LLMClient, MockLLMClient


class TestLLMClientAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError, match="abstract method"):
            LLMClient()

    def test_has_abstract_generate_method(self):
        assert "generate" in LLMClient.__abstractmethods__


class TestMockLLMClient:
    def test_single_response_returned_every_time(self):
        client = MockLLMClient(["hello"])
        assert client.generate("sys", "user") == "hello"
        assert client.generate("sys", "user2") == "hello"
        assert client.generate("sys", "user3") == "hello"

    def test_cycles_through_multiple_responses(self):
        client = MockLLMClient(["a", "b", "c"])
        assert client.generate("s", "u") == "a"
        assert client.generate("s", "u") == "b"
        assert client.generate("s", "u") == "c"
        # Wraps around
        assert client.generate("s", "u") == "a"

    def test_calls_tracks_system_and_user_prompts(self):
        client = MockLLMClient(["ok"])
        client.generate("system1", "user1")
        client.generate("system2", "user2")
        assert client.calls == [("system1", "user1"), ("system2", "user2")]

    def test_calls_starts_empty(self):
        client = MockLLMClient(["ok"])
        assert client.calls == []

    def test_ignores_temperature_parameter(self):
        client = MockLLMClient(["result"])
        assert client.generate("s", "u", temperature=0.0) == "result"
        assert client.generate("s", "u", temperature=1.0) == "result"
        assert len(client.calls) == 2

    def test_index_increments_on_each_call(self):
        client = MockLLMClient(["x", "y"])
        assert client._index == 0
        client.generate("s", "u")
        assert client._index == 1
        client.generate("s", "u")
        assert client._index == 2

    def test_empty_responses_raises_zero_division(self):
        client = MockLLMClient([])
        with pytest.raises(ZeroDivisionError):
            client.generate("s", "u")

    def test_is_subclass_of_llm_client(self):
        assert issubclass(MockLLMClient, LLMClient)
        client = MockLLMClient(["test"])
        assert isinstance(client, LLMClient)

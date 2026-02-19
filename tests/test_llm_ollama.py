"""Tests for marketing_engine.llm.ollama."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from marketing_engine.exceptions import LLMError
from marketing_engine.llm.base import LLMClient
from marketing_engine.llm.ollama import OllamaClient


def _make_response(json_data: dict | None = None, *, status_code: int = 200, text: str = ""):
    """Create a mock httpx.Response with the needed attributes."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or str(json_data)
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("No JSON")
    resp.raise_for_status.return_value = None
    return resp


class TestOllamaClientInit:
    def test_default_host_localhost(self):
        client = OllamaClient()
        assert client.host == "http://localhost:11434"

    def test_default_model_llama32(self):
        client = OllamaClient()
        assert client.model == "llama3.2"

    def test_custom_model_and_host(self):
        client = OllamaClient(model="mistral", host="http://gpu-box:11434")
        assert client.model == "mistral"
        assert client.host == "http://gpu-box:11434"

    def test_respects_ollama_host_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://remote:9999")
        client = OllamaClient()
        assert client.host == "http://remote:9999"

    def test_explicit_host_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://remote:9999")
        client = OllamaClient(host="http://explicit:1234")
        assert client.host == "http://explicit:1234"

    def test_is_subclass_of_llm_client(self):
        assert issubclass(OllamaClient, LLMClient)


class TestOllamaClientGenerate:
    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_sends_correct_payload(self, mock_post):
        mock_post.return_value = _make_response({"response": "ok"})
        client = OllamaClient(model="llama3.2", host="http://localhost:11434")
        client.generate("sys prompt", "user prompt", temperature=0.5)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["model"] == "llama3.2"
        assert call_kwargs[1]["json"]["system"] == "sys prompt"
        assert call_kwargs[1]["json"]["prompt"] == "user prompt"
        assert call_kwargs[1]["json"]["stream"] is False
        assert call_kwargs[1]["json"]["options"]["temperature"] == 0.5

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_posts_to_api_generate_url(self, mock_post):
        mock_post.return_value = _make_response({"response": "ok"})
        client = OllamaClient(host="http://myhost:11434")
        client.generate("s", "u")

        url = mock_post.call_args[0][0]
        assert url == "http://myhost:11434/api/generate"

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_returns_response_field(self, mock_post):
        mock_post.return_value = _make_response({"response": "Generated text here"})
        client = OllamaClient()
        result = client.generate("s", "u")
        assert result == "Generated text here"

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_timeout_raises_llm_error(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timed out")
        client = OllamaClient()
        with pytest.raises(LLMError, match="timed out"):
            client.generate("s", "u")

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_http_status_error_raises_llm_error(self, mock_post):
        request = httpx.Request("POST", "http://localhost:11434/api/generate")
        response = httpx.Response(status_code=500, text="Internal Server Error", request=request)
        mock_post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=request, response=response
        )
        client = OllamaClient()
        with pytest.raises(LLMError, match="HTTP 500"):
            client.generate("s", "u")

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_connection_error_raises_llm_error(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = OllamaClient()
        with pytest.raises(LLMError, match="request failed"):
            client.generate("s", "u")

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_invalid_json_raises_llm_error(self, mock_post):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("Expecting value")
        resp.text = "not json at all"
        mock_post.return_value = resp
        client = OllamaClient()
        with pytest.raises(LLMError, match="invalid JSON"):
            client.generate("s", "u")

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_missing_response_key_raises_llm_error(self, mock_post):
        mock_post.return_value = _make_response({"model": "llama3.2", "done": True})
        client = OllamaClient()
        with pytest.raises(LLMError, match="missing 'response' key"):
            client.generate("s", "u")

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_temperature_passed_in_options(self, mock_post):
        mock_post.return_value = _make_response({"response": "ok"})
        client = OllamaClient()
        client.generate("s", "u", temperature=0.3)
        options = mock_post.call_args[1]["json"]["options"]
        assert options["temperature"] == 0.3

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_host_trailing_slash_stripped(self, mock_post):
        mock_post.return_value = _make_response({"response": "ok"})
        client = OllamaClient(host="http://localhost:11434/")
        client.generate("s", "u")

        url = mock_post.call_args[0][0]
        assert url == "http://localhost:11434/api/generate"
        assert "//" not in url.replace("http://", "", 1)

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_timeout_value_set(self, mock_post):
        mock_post.return_value = _make_response({"response": "ok"})
        client = OllamaClient()
        client.generate("s", "u")
        assert mock_post.call_args[1]["timeout"] == 120.0

    @patch("marketing_engine.llm.ollama.httpx.post")
    def test_generic_http_error_raises_llm_error(self, mock_post):
        mock_post.side_effect = httpx.HTTPError("generic error")
        client = OllamaClient()
        with pytest.raises(LLMError, match="request failed"):
            client.generate("s", "u")

"""Tests for timeless_clips.extract_moment — MomentExtractor."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from timeless_clips.extract_moment import _SYSTEM_PROMPT, MomentExtractor
from timeless_clips.models import ArchiveItem, ShortScript


def _make_item(**overrides) -> ArchiveItem:
    """Helper to build an ArchiveItem with sensible defaults."""
    defaults = {
        "identifier": "test-film-001",
        "title": "Test Film",
        "collection": "prelinger",
        "source_url": "https://archive.org/details/test-film-001",
        "category": "educational",
    }
    defaults.update(overrides)
    return ArchiveItem(**defaults)


def _make_config(**llm_overrides) -> dict:
    """Config dict with optional LLM overrides."""
    llm = {"host": "http://localhost:11434", "model": "llama3.2"}
    llm.update(llm_overrides)
    return {"llm": llm}


def _make_llm_response(**overrides) -> dict:
    """A complete LLM JSON response with sensible defaults."""
    data = {
        "hook": "You won't believe what schools taught",
        "start_time": 30.0,
        "end_time": 60.0,
        "narration": "In 1951, the government released this chilling film.",
        "text_overlays": [
            {"time": 0.0, "text": "1951", "position": "top-right"},
            {"time": 3.0, "text": "Duck and Cover", "position": "bottom"},
        ],
        "closing": "Follow for more cold war secrets.",
        "category": "educational",
        "mood": "eerie",
        "tags": ["cold-war", "1950s"],
    }
    data.update(overrides)
    return data


class TestBuildPrompt:
    """_build_prompt formats item metadata for the LLM."""

    def test_includes_title(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(title="Duck and Cover")
        prompt = extractor._build_prompt(item)
        assert "Title: Duck and Cover" in prompt

    def test_includes_year(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(year=1951)
        prompt = extractor._build_prompt(item)
        assert "Year: 1951" in prompt

    def test_year_unknown_when_none(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(year=None)
        prompt = extractor._build_prompt(item)
        assert "Year: Unknown" in prompt

    def test_includes_collection(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(collection="feature_films")
        prompt = extractor._build_prompt(item)
        assert "Collection: feature_films" in prompt

    def test_includes_category(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(category="newsreel")
        prompt = extractor._build_prompt(item)
        assert "Category: newsreel" in prompt

    def test_includes_description_truncated(self) -> None:
        extractor = MomentExtractor(_make_config())
        long_desc = "A" * 600
        item = _make_item(description=long_desc)
        prompt = extractor._build_prompt(item)
        assert "Description:" in prompt
        # Truncated to 500 chars
        assert f"Description: {'A' * 500}" in prompt
        assert "A" * 501 not in prompt

    def test_omits_description_when_empty(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(description="")
        prompt = extractor._build_prompt(item)
        assert "Description:" not in prompt

    def test_includes_duration(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(duration=540.0)
        prompt = extractor._build_prompt(item)
        assert "Duration: 540 seconds" in prompt

    def test_omits_duration_when_none(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(duration=None)
        prompt = extractor._build_prompt(item)
        assert "Duration:" not in prompt

    def test_includes_tags(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(tags=["cold-war", "education"])
        prompt = extractor._build_prompt(item)
        assert "Tags: cold-war, education" in prompt

    def test_omits_tags_when_empty(self) -> None:
        extractor = MomentExtractor(_make_config())
        item = _make_item(tags=[])
        prompt = extractor._build_prompt(item)
        assert "Tags:" not in prompt


class TestParseResponse:
    """_parse_response handles clean JSON, fenced JSON, and failures."""

    def test_parses_clean_json(self) -> None:
        extractor = MomentExtractor(_make_config())
        data = {"hook": "Test", "start_time": 0}
        result = extractor._parse_response(json.dumps(data))
        assert result == data

    def test_parses_fenced_json(self) -> None:
        extractor = MomentExtractor(_make_config())
        raw = '```json\n{"hook": "Fenced", "start_time": 5}\n```'
        result = extractor._parse_response(raw)
        assert result["hook"] == "Fenced"
        assert result["start_time"] == 5

    def test_parses_fenced_no_language_tag(self) -> None:
        extractor = MomentExtractor(_make_config())
        raw = '```\n{"hook": "Plain fenced"}\n```'
        result = extractor._parse_response(raw)
        assert result["hook"] == "Plain fenced"

    def test_invalid_json_returns_empty_dict(self) -> None:
        extractor = MomentExtractor(_make_config())
        result = extractor._parse_response("This is not JSON at all")
        assert result == {}

    def test_empty_string_returns_empty_dict(self) -> None:
        extractor = MomentExtractor(_make_config())
        result = extractor._parse_response("")
        assert result == {}

    def test_parses_json_with_whitespace(self) -> None:
        extractor = MomentExtractor(_make_config())
        raw = '  \n  {"hook": "Padded"}  \n  '
        result = extractor._parse_response(raw)
        assert result["hook"] == "Padded"


class TestCallLLM:
    """_call_llm sends correct POST request to Ollama."""

    def test_posts_to_ollama_generate(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": '{"hook": "result"}'}
        mock_client.post.return_value = mock_response

        extractor = MomentExtractor(_make_config(), client=mock_client)
        result = extractor._call_llm("test prompt")

        assert result == '{"hook": "result"}'
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "system": _SYSTEM_PROMPT,
                "prompt": "test prompt",
                "stream": False,
            },
        )
        mock_response.raise_for_status.assert_called_once()

    def test_returns_empty_string_when_no_response_key(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_client.post.return_value = mock_response

        extractor = MomentExtractor(_make_config(), client=mock_client)
        result = extractor._call_llm("test")
        assert result == ""

    def test_uses_custom_model_and_host(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "{}"}
        mock_client.post.return_value = mock_response

        config = _make_config(host="http://custom:8080", model="mixtral")
        extractor = MomentExtractor(config, client=mock_client)
        extractor._call_llm("prompt")

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://custom:8080/api/generate"
        assert call_args[1]["json"]["model"] == "mixtral"


class TestExtract:
    """extract integration — mock LLM call, verify ShortScript output."""

    def _setup_extractor(self, llm_response: dict) -> MomentExtractor:
        """Build an extractor with a mocked client returning the given dict."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(llm_response)}
        mock_client.post.return_value = mock_resp
        return MomentExtractor(_make_config(), client=mock_client)

    def test_extract_returns_short_script(self) -> None:
        response = _make_llm_response()
        extractor = self._setup_extractor(response)
        item = _make_item()

        script = extractor.extract(item)

        assert isinstance(script, ShortScript)
        assert script.item_id == "test-film-001"
        assert script.hook == response["hook"]
        assert script.start_time == 30.0
        assert script.end_time == 60.0
        assert script.narration == response["narration"]
        assert script.closing == response["closing"]
        assert script.category == "educational"
        assert script.mood == "eerie"
        assert script.tags == ["cold-war", "1950s"]

    def test_extract_text_overlays(self) -> None:
        response = _make_llm_response()
        extractor = self._setup_extractor(response)
        item = _make_item()

        script = extractor.extract(item)

        assert len(script.text_overlays) == 2
        assert script.text_overlays[0].time == 0.0
        assert script.text_overlays[0].text == "1951"
        assert script.text_overlays[0].position == "top-right"
        assert script.text_overlays[1].text == "Duck and Cover"
        assert script.text_overlays[1].position == "bottom"

    def test_extract_defaults_on_empty_response(self) -> None:
        extractor = self._setup_extractor({})
        item = _make_item(category="newsreel")

        script = extractor.extract(item)

        assert script.item_id == "test-film-001"
        assert script.hook == ""
        assert script.start_time == 0.0
        assert script.end_time == 60.0
        assert script.narration == ""
        assert script.text_overlays == []
        assert script.closing == ""
        assert script.category == "newsreel"  # Falls back to item.category
        assert script.mood == "nostalgic"
        assert script.tags == []

    def test_extract_partial_response(self) -> None:
        extractor = self._setup_extractor({"hook": "Just a hook", "mood": "dramatic"})
        item = _make_item()

        script = extractor.extract(item)

        assert script.hook == "Just a hook"
        assert script.mood == "dramatic"
        assert script.start_time == 0.0
        assert script.end_time == 60.0

    def test_extract_overlay_defaults(self) -> None:
        """Overlay with missing fields gets defaults."""
        response = _make_llm_response(
            text_overlays=[{"text": "Bare overlay"}],
        )
        extractor = self._setup_extractor(response)
        item = _make_item()

        script = extractor.extract(item)

        assert len(script.text_overlays) == 1
        assert script.text_overlays[0].time == 0
        assert script.text_overlays[0].text == "Bare overlay"
        assert script.text_overlays[0].position == "bottom"


class TestMomentExtractorDefaults:
    """Constructor defaults when config keys are missing."""

    def test_default_host(self) -> None:
        extractor = MomentExtractor({})
        assert extractor._host == "http://localhost:11434"

    def test_default_model(self) -> None:
        extractor = MomentExtractor({})
        assert extractor._model == "llama3.2"

    def test_custom_client_injected(self) -> None:
        mock_client = MagicMock()
        extractor = MomentExtractor({}, client=mock_client)
        assert extractor._client is mock_client

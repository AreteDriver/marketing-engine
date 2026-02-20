"""Tests for timeless_clips.narration — NarrationGenerator, StubEngine, PiperEngine."""

from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from timeless_clips.models import ShortScript
from timeless_clips.narration import (
    NarrationGenerator,
    PiperEngine,
    StubEngine,
)


def _make_script(**overrides) -> ShortScript:
    """Helper to build a ShortScript with sensible defaults."""
    defaults = {
        "item_id": "test-narr-001",
        "hook": "You won't believe this",
        "start_time": 0.0,
        "end_time": 30.0,
        "narration": "In 1951, something amazing happened.",
        "closing": "Follow for more history.",
    }
    defaults.update(overrides)
    return ShortScript(**defaults)


class TestStubEngine:
    """StubEngine creates a minimal valid WAV file."""

    def test_creates_wav_file(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "test.wav"
        result = engine.synthesize("Hello world", output)
        assert result == output
        assert output.exists()

    def test_wav_is_44_bytes(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "test.wav"
        engine.synthesize("Hello world", output)
        assert output.stat().st_size == 44

    def test_wav_has_riff_header(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "test.wav"
        engine.synthesize("Text", output)
        data = output.read_bytes()
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"

    def test_wav_has_fmt_chunk(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "test.wav"
        engine.synthesize("Text", output)
        data = output.read_bytes()
        assert data[12:16] == b"fmt "
        # PCM format = 1
        fmt_code = struct.unpack("<H", data[20:22])[0]
        assert fmt_code == 1

    def test_wav_has_data_chunk(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "test.wav"
        engine.synthesize("Text", output)
        data = output.read_bytes()
        assert data[36:40] == b"data"
        # Zero-length data
        data_size = struct.unpack("<I", data[40:44])[0]
        assert data_size == 0

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "nested" / "deep" / "test.wav"
        result = engine.synthesize("Text", output)
        assert result.exists()

    def test_returns_output_path(self, tmp_path: Path) -> None:
        engine = StubEngine()
        output = tmp_path / "result.wav"
        result = engine.synthesize("Text", output)
        assert result == output


class TestPiperEngine:
    """PiperEngine calls piper subprocess."""

    def test_success(self, tmp_path: Path) -> None:
        engine = PiperEngine(voice="en_US-lessac-medium")
        output = tmp_path / "piper_out.wav"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("timeless_clips.narration.subprocess.run", return_value=mock_result) as mock_run:
            result = engine.synthesize("Hello", output)

        assert result == output
        mock_run.assert_called_once_with(
            ["piper", "--model", "en_US-lessac-medium", "--output_file", str(output)],
            input="Hello",
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_failure_raises_runtime_error(self, tmp_path: Path) -> None:
        engine = PiperEngine()
        output = tmp_path / "fail.wav"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Model not found"

        with (
            patch("timeless_clips.narration.subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="Piper TTS failed: Model not found"),
        ):
            engine.synthesize("Hello", output)

    def test_custom_voice(self) -> None:
        engine = PiperEngine(voice="en_GB-alan-low")
        assert engine._voice == "en_GB-alan-low"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        engine = PiperEngine()
        output = tmp_path / "nested" / "dir" / "out.wav"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("timeless_clips.narration.subprocess.run", return_value=mock_result):
            engine.synthesize("Hello", output)

        assert output.parent.exists()


class TestNarrationGenerator:
    """NarrationGenerator wires engine selection and text assembly."""

    def test_injected_engine_used(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = tmp_path / "out.wav"
        gen = NarrationGenerator({}, engine=mock_engine)
        script = _make_script()

        gen.generate(script, tmp_path)

        mock_engine.synthesize.assert_called_once()

    def test_piper_engine_default(self) -> None:
        gen = NarrationGenerator({"tts": {"engine": "piper", "voice": "en_US-lessac-medium"}})
        assert isinstance(gen._engine, PiperEngine)

    def test_non_piper_defaults_to_stub(self) -> None:
        gen = NarrationGenerator({"tts": {"engine": "stub"}})
        assert isinstance(gen._engine, StubEngine)

    def test_missing_engine_config_defaults_to_piper(self) -> None:
        gen = NarrationGenerator({"tts": {}})
        assert isinstance(gen._engine, PiperEngine)

    def test_empty_config_defaults_to_piper(self) -> None:
        gen = NarrationGenerator({})
        assert isinstance(gen._engine, PiperEngine)

    def test_generate_combines_hook_narration_closing(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = tmp_path / "out.wav"
        gen = NarrationGenerator({}, engine=mock_engine)
        script = _make_script(
            hook="Hook text",
            narration="Narration text",
            closing="Closing text",
        )

        gen.generate(script, tmp_path)

        call_args = mock_engine.synthesize.call_args
        text = call_args[0][0]
        assert text == "Hook text Narration text Closing text"

    def test_generate_skips_empty_parts(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = tmp_path / "out.wav"
        gen = NarrationGenerator({}, engine=mock_engine)
        script = _make_script(hook="", narration="Only narration", closing="")

        gen.generate(script, tmp_path)

        call_args = mock_engine.synthesize.call_args
        text = call_args[0][0]
        assert text == "Only narration"

    def test_generate_output_filename(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = tmp_path / "test-narr-001_narration.wav"
        gen = NarrationGenerator({}, engine=mock_engine)
        script = _make_script(item_id="test-narr-001")

        gen.generate(script, tmp_path)

        call_args = mock_engine.synthesize.call_args
        output_path = call_args[0][1]
        assert output_path == tmp_path / "test-narr-001_narration.wav"

    def test_generate_returns_engine_result(self, tmp_path: Path) -> None:
        expected = tmp_path / "result.wav"
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = expected
        gen = NarrationGenerator({}, engine=mock_engine)

        result = gen.generate(_make_script(), tmp_path)
        assert result == expected

    def test_generate_all_empty_parts(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = tmp_path / "out.wav"
        gen = NarrationGenerator({}, engine=mock_engine)
        script = _make_script(hook="", narration="", closing="")

        gen.generate(script, tmp_path)

        call_args = mock_engine.synthesize.call_args
        text = call_args[0][0]
        assert text == ""

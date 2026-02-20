"""Tests for timeless_clips.captions — CaptionGenerator, engines, SRT formatting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from timeless_clips.captions import (
    CaptionGenerator,
    StubCaptionEngine,
    WhisperEngine,
    _format_srt_time,
)


class TestFormatSrtTime:
    """_format_srt_time converts seconds to HH:MM:SS,mmm."""

    def test_zero(self) -> None:
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_seconds_only(self) -> None:
        assert _format_srt_time(5.0) == "00:00:05,000"

    def test_milliseconds(self) -> None:
        assert _format_srt_time(1.234) == "00:00:01,234"

    def test_minutes(self) -> None:
        assert _format_srt_time(125.0) == "00:02:05,000"

    def test_hours(self) -> None:
        assert _format_srt_time(3661.5) == "01:01:01,500"

    def test_large_value(self) -> None:
        # 2 hours, 30 minutes, 15.75 seconds
        assert _format_srt_time(9015.75) == "02:30:15,750"

    def test_fractional_second(self) -> None:
        assert _format_srt_time(0.5) == "00:00:00,500"

    def test_59_seconds(self) -> None:
        assert _format_srt_time(59.0) == "00:00:59,000"


class TestSegmentsToSrt:
    """WhisperEngine._segments_to_srt formats segments as SRT."""

    def test_single_segment(self) -> None:
        segments = [{"start": 0.0, "end": 5.0, "text": "Hello world"}]
        result = WhisperEngine._segments_to_srt(segments)
        lines = result.split("\n")
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:05,000"
        assert lines[2] == "Hello world"
        assert lines[3] == ""

    def test_multiple_segments(self) -> None:
        segments = [
            {"start": 0.0, "end": 3.0, "text": "First line"},
            {"start": 3.5, "end": 7.0, "text": "Second line"},
            {"start": 7.5, "end": 10.0, "text": "Third line"},
        ]
        result = WhisperEngine._segments_to_srt(segments)
        lines = result.split("\n")
        # Segment 1
        assert lines[0] == "1"
        assert lines[2] == "First line"
        # Segment 2
        assert lines[4] == "2"
        assert lines[6] == "Second line"
        # Segment 3
        assert lines[8] == "3"
        assert lines[10] == "Third line"

    def test_empty_segments(self) -> None:
        result = WhisperEngine._segments_to_srt([])
        assert result == ""

    def test_segment_text_stripped(self) -> None:
        segments = [{"start": 0.0, "end": 1.0, "text": "  padded text  "}]
        result = WhisperEngine._segments_to_srt(segments)
        assert "padded text" in result
        assert "  padded text  " not in result

    def test_segment_missing_fields_use_defaults(self) -> None:
        segments = [{}]
        result = WhisperEngine._segments_to_srt(segments)
        lines = result.split("\n")
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:00,000"
        assert lines[2] == ""


class TestStubCaptionEngine:
    """StubCaptionEngine writes a minimal SRT file."""

    def test_creates_srt_file(self, tmp_path: Path) -> None:
        engine = StubCaptionEngine()
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"fake")
        output = tmp_path / "captions.srt"

        result = engine.transcribe(audio, output)

        assert result == output
        assert output.exists()

    def test_srt_content(self, tmp_path: Path) -> None:
        engine = StubCaptionEngine(text="Test caption")
        output = tmp_path / "captions.srt"

        engine.transcribe(tmp_path / "audio.wav", output)

        content = output.read_text()
        assert "1\n" in content
        assert "00:00:00,000 --> 00:00:05,000" in content
        assert "Test caption" in content

    def test_custom_text(self, tmp_path: Path) -> None:
        engine = StubCaptionEngine(text="Custom text here")
        output = tmp_path / "captions.srt"
        engine.transcribe(tmp_path / "audio.wav", output)
        content = output.read_text()
        assert "Custom text here" in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        engine = StubCaptionEngine()
        output = tmp_path / "nested" / "dir" / "captions.srt"
        engine.transcribe(tmp_path / "audio.wav", output)
        assert output.exists()

    def test_default_text(self) -> None:
        engine = StubCaptionEngine()
        assert engine._text == "Sample caption text"


class TestWhisperEngineTranscribe:
    """WhisperEngine.transcribe with mocked whisper module."""

    def test_transcribe_writes_srt(self, tmp_path: Path) -> None:
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Hello world"},
            ],
        }
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            engine = WhisperEngine(model="base", language="en")
            audio = tmp_path / "audio.wav"
            audio.write_bytes(b"fake")
            output = tmp_path / "captions.srt"

            result = engine.transcribe(audio, output)

        assert result == output
        content = output.read_text()
        assert "Hello world" in content
        mock_whisper.load_model.assert_called_once_with("base")
        mock_model.transcribe.assert_called_once_with(str(audio), language="en")

    def test_lazy_model_loading(self) -> None:
        engine = WhisperEngine(model="small")
        assert engine._model is None

    def test_model_loaded_once(self, tmp_path: Path) -> None:
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"segments": []}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            engine = WhisperEngine()
            audio = tmp_path / "audio.wav"
            audio.write_bytes(b"fake")

            engine.transcribe(audio, tmp_path / "out1.srt")
            engine.transcribe(audio, tmp_path / "out2.srt")

        # load_model called once, transcribe called twice
        mock_whisper.load_model.assert_called_once()
        assert mock_model.transcribe.call_count == 2

    def test_creates_output_parent_dir(self, tmp_path: Path) -> None:
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"segments": []}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            engine = WhisperEngine()
            audio = tmp_path / "audio.wav"
            audio.write_bytes(b"fake")
            output = tmp_path / "nested" / "captions.srt"

            engine.transcribe(audio, output)

        assert output.parent.exists()


class TestCaptionGenerator:
    """CaptionGenerator wires engine selection and output naming."""

    def test_injected_engine_used(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.transcribe.return_value = tmp_path / "out.srt"
        gen = CaptionGenerator({}, engine=mock_engine)

        gen.generate(tmp_path / "audio.wav", tmp_path, "item-001")

        mock_engine.transcribe.assert_called_once()

    def test_whisper_import_failure_falls_back_to_stub(self) -> None:
        with patch("timeless_clips.captions.WhisperEngine") as mock_cls:
            mock_cls.side_effect = ImportError("No module named 'whisper'")
            gen = CaptionGenerator({"captions": {"model": "base", "language": "en"}})
        assert isinstance(gen._engine, StubCaptionEngine)

    def test_whisper_engine_created_by_default(self) -> None:
        with patch("timeless_clips.captions.WhisperEngine") as mock_cls:
            mock_cls.return_value = MagicMock()
            gen = CaptionGenerator({"captions": {"model": "small", "language": "fr"}})
        mock_cls.assert_called_once_with(model="small", language="fr")
        assert gen._engine is mock_cls.return_value

    def test_generate_output_filename(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.transcribe.return_value = tmp_path / "item-001_captions.srt"
        gen = CaptionGenerator({}, engine=mock_engine)

        gen.generate(tmp_path / "audio.wav", tmp_path, "item-001")

        call_args = mock_engine.transcribe.call_args
        output_path = call_args[0][1]
        assert output_path == tmp_path / "item-001_captions.srt"

    def test_generate_passes_audio_path(self, tmp_path: Path) -> None:
        mock_engine = MagicMock()
        mock_engine.transcribe.return_value = tmp_path / "out.srt"
        gen = CaptionGenerator({}, engine=mock_engine)
        audio = tmp_path / "my_audio.wav"

        gen.generate(audio, tmp_path, "item-001")

        call_args = mock_engine.transcribe.call_args
        assert call_args[0][0] == audio

    def test_generate_returns_engine_result(self, tmp_path: Path) -> None:
        expected = tmp_path / "result.srt"
        mock_engine = MagicMock()
        mock_engine.transcribe.return_value = expected
        gen = CaptionGenerator({}, engine=mock_engine)

        result = gen.generate(tmp_path / "audio.wav", tmp_path, "item-001")
        assert result == expected

    def test_default_config_values(self) -> None:
        with patch("timeless_clips.captions.WhisperEngine") as mock_cls:
            mock_cls.return_value = MagicMock()
            CaptionGenerator({})
        mock_cls.assert_called_once_with(model="base", language="en")

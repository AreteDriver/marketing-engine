"""Caption generation using Whisper."""

from __future__ import annotations

import abc
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CaptionEngine(abc.ABC):
    """Abstract base for caption engines."""

    @abc.abstractmethod
    def transcribe(self, audio_path: Path, output_path: Path) -> Path:
        """Generate SRT captions from audio. Returns SRT path."""


class WhisperEngine(CaptionEngine):
    """Caption generation using OpenAI Whisper."""

    def __init__(self, model: str = "base", language: str = "en") -> None:
        self._model_name = model
        self._language = language
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            import whisper

            self._model = whisper.load_model(self._model_name)

    def transcribe(self, audio_path: Path, output_path: Path) -> Path:
        self._load_model()
        result = self._model.transcribe(
            str(audio_path),
            language=self._language,
        )
        srt_content = self._segments_to_srt(result.get("segments", []))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content)
        return output_path

    @staticmethod
    def _segments_to_srt(segments: list[dict]) -> str:
        """Convert Whisper segments to SRT format."""
        lines: list[str] = []
        for i, seg in enumerate(segments, 1):
            start = _format_srt_time(seg.get("start", 0))
            end = _format_srt_time(seg.get("end", 0))
            text = seg.get("text", "").strip()
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)


class StubCaptionEngine(CaptionEngine):
    """Stub engine that creates a minimal SRT for testing."""

    def __init__(self, text: str = "Sample caption text") -> None:
        self._text = text

    def transcribe(self, audio_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        srt = f"1\n00:00:00,000 --> 00:00:05,000\n{self._text}\n\n"
        output_path.write_text(srt)
        return output_path


class CaptionGenerator:
    """Generate captions for narration audio."""

    def __init__(
        self,
        config: dict,
        engine: CaptionEngine | None = None,
    ) -> None:
        cap_config = config.get("captions", {})
        if engine is not None:
            self._engine = engine
        else:
            model = cap_config.get("model", "base")
            language = cap_config.get("language", "en")
            try:
                self._engine = WhisperEngine(model=model, language=language)
            except ImportError:
                logger.warning("Whisper not installed, using stub captions")
                self._engine = StubCaptionEngine()

    def generate(self, audio_path: Path, output_dir: Path, item_id: str) -> Path:
        """Generate SRT captions from narration audio."""
        output_path = output_dir / f"{item_id}_captions.srt"
        return self._engine.transcribe(audio_path, output_path)


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

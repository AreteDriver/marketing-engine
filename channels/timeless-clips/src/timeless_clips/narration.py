"""TTS narration generation."""

from __future__ import annotations

import abc
import logging
import struct
import subprocess
from pathlib import Path

from timeless_clips.models import ShortScript

logger = logging.getLogger(__name__)


class NarrationEngine(abc.ABC):
    """Abstract base for TTS engines."""

    @abc.abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Generate WAV audio from text. Returns output path."""


class PiperEngine(NarrationEngine):
    """Local TTS using Piper."""

    def __init__(self, voice: str = "en_US-lessac-medium") -> None:
        self._voice = voice

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "piper",
            "--model",
            self._voice,
            "--output_file",
            str(output_path),
        ]
        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {result.stderr}")
        return output_path


class StubEngine(NarrationEngine):
    """Stub engine that creates an empty WAV for testing."""

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write minimal WAV header (44 bytes)
        with open(output_path, "wb") as f:
            # RIFF header
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36))  # file size - 8
            f.write(b"WAVE")
            # fmt chunk
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))  # chunk size
            f.write(struct.pack("<H", 1))  # PCM format
            f.write(struct.pack("<H", 1))  # mono
            f.write(struct.pack("<I", 22050))  # sample rate
            f.write(struct.pack("<I", 22050))  # byte rate
            f.write(struct.pack("<H", 1))  # block align
            f.write(struct.pack("<H", 8))  # bits per sample
            # data chunk
            f.write(b"data")
            f.write(struct.pack("<I", 0))  # data size
        return output_path


class NarrationGenerator:
    """Generate narration audio for Short scripts."""

    def __init__(
        self,
        config: dict,
        engine: NarrationEngine | None = None,
    ) -> None:
        tts_config = config.get("tts", {})
        engine_name = tts_config.get("engine", "piper")
        if engine is not None:
            self._engine = engine
        elif engine_name == "piper":
            voice = tts_config.get("voice", "en_US-lessac-medium")
            self._engine = PiperEngine(voice=voice)
        else:
            self._engine = StubEngine()

    def generate(self, script: ShortScript, output_dir: Path) -> Path:
        """Generate narration WAV from a script."""
        # Combine hook + narration + closing
        parts: list[str] = []
        if script.hook:
            parts.append(script.hook)
        if script.narration:
            parts.append(script.narration)
        if script.closing:
            parts.append(script.closing)
        text = " ".join(parts)

        output_path = output_dir / f"{script.item_id}_narration.wav"
        return self._engine.synthesize(text, output_path)

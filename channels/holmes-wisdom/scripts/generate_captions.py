#!/usr/bin/env python3
"""
Generate word-level captions using Whisper for burned-in subtitles.
Critical for Shorts engagement — most viewers watch without sound.

Usage:
    python scripts/generate_captions.py [audio_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "captions"


def format_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(audio_path: str, output_path: str) -> None:
    """Generate SRT captions from audio using Whisper."""
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
    )

    # Build SRT from word-level timestamps
    # Group into 3-5 word phrases for animated caption style
    words = []
    for segment in result["segments"]:
        if "words" in segment:
            words.extend(segment["words"])

    srt_entries = []
    idx = 1
    group_size = 4
    for i in range(0, len(words), group_size):
        group = words[i : i + group_size]
        start = group[0]["start"]
        end = group[-1]["end"]
        text = " ".join(w["word"].strip() for w in group)

        srt_entries.append(f"{idx}\n{format_time(start)} --> {format_time(end)}\n{text}\n")
        idx += 1

    Path(output_path).write_text("\n".join(srt_entries))


def process_audio(audio_dir: str, output_dir: str) -> None:
    """Generate captions for all audio files."""
    audio_path = Path(audio_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for audio_file in sorted(audio_path.glob("*.wav")):
        print(f"[->] Generating captions: {audio_file.name}")
        out_file = output_path / f"{audio_file.stem}.srt"
        try:
            generate_srt(str(audio_file), str(out_file))
            print(f"  [+] Captions saved: {out_file.name}")
        except Exception as e:
            print(f"  [x] Caption generation failed: {e}")


if __name__ == "__main__":
    audio_dir = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent.parent / "output" / "audio")
    )
    process_audio(audio_dir, str(OUTPUT_DIR))

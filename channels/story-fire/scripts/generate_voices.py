#!/usr/bin/env python3
"""
VOICE Agent — Two-character narration system for Story Fire.

Generates Storyteller and Dog voices separately, then composites
with appropriate pauses and ambient sound (fire crackle).

Usage:
    python scripts/generate_voices.py [scripts_dir]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Voice configurations
STORYTELLER_PIPER_MODEL = str(BASE_DIR / "models" / "piper" / "voice-en-us-lessac-medium.onnx")
DOG_PIPER_MODEL = str(BASE_DIR / "models" / "piper" / "voice-en-us-lessac-medium.onnx")

# ElevenLabs config (optional upgrade)
USE_ELEVENLABS = False
ELEVENLABS_API_KEY = ""
STORYTELLER_VOICE_ID = "adam"  # Deep, warm
DOG_VOICE_ID = "charlie"  # Distinct, slightly nasal

OUTPUT_DIR = BASE_DIR / "output" / "audio"

# Ambient sound
FIRE_CRACKLE = str(BASE_DIR / "assets" / "audio" / "fire_crackle_loop.wav")
AMBIENT_VOLUME = 0.08


def generate_piper_audio(text: str, model: str, output_path: str) -> None:
    """Generate audio using local Piper TTS."""
    cmd = ["piper", "--model", model, "--output_file", output_path]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        raise RuntimeError(f"Piper failed: {stderr.decode()}")


def generate_silence(duration: float, output_path: str) -> None:
    """Generate a silence audio segment."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=22050:cl=mono",
        "-t",
        str(duration),
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def parse_vocal_cues(text: str) -> list[dict]:
    """Parse [pause], [whisper], [louder] markers from narration."""
    segments: list[dict] = []
    current: dict = {"text": "", "intensity": "normal"}

    for part in re.split(r"(\[.*?\])", text):
        if part == "[pause]":
            if current["text"].strip():
                segments.append(current)
            segments.append({"text": "", "type": "pause", "duration": 0.6})
            current = {"text": "", "intensity": "normal"}
        elif part == "[whisper]":
            if current["text"].strip():
                segments.append(current)
            current = {"text": "", "intensity": "whisper"}
        elif part == "[louder]":
            if current["text"].strip():
                segments.append(current)
            current = {"text": "", "intensity": "loud"}
        else:
            current["text"] += part

    if current["text"].strip():
        segments.append(current)

    return segments


def build_audio_sequence(script: dict) -> list[dict]:
    """Build the narration sequence from a Storyteller script."""
    sequence: list[dict] = []

    # Hook (Storyteller)
    if script.get("hook"):
        sequence.append({"voice": "storyteller", "text": script["hook"]})

    # Dog reaction
    if script.get("dog_reaction"):
        sequence.append({"type": "pause", "duration": 0.4})
        sequence.append({"voice": "dog", "text": script["dog_reaction"]})
        sequence.append({"type": "pause", "duration": 0.3})

    # Core narration (Storyteller) — with vocal cue parsing
    if script.get("narration"):
        segments = parse_vocal_cues(script["narration"])
        for seg in segments:
            if seg.get("type") == "pause":
                sequence.append(seg)
            elif seg["text"].strip():
                sequence.append({"voice": "storyteller", "text": seg["text"]})

    # Dog interjection (mid-story)
    if script.get("dog_interjection"):
        sequence.append({"type": "pause", "duration": 0.3})
        sequence.append({"voice": "dog", "text": script["dog_interjection"]})
        sequence.append({"type": "pause", "duration": 0.3})

    # Closing (Storyteller)
    if script.get("closing"):
        sequence.append({"type": "pause", "duration": 0.5})
        sequence.append({"voice": "storyteller", "text": script["closing"]})

    # Dog's last word
    if script.get("dog_closing"):
        sequence.append({"type": "pause", "duration": 0.4})
        sequence.append({"voice": "dog", "text": script["dog_closing"]})

    return sequence


def render_sequence(sequence: list[dict], output_path: str) -> None:
    """Render audio sequence to a single WAV file via FFmpeg concat."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parts: list[str] = []
        concat_list = Path(tmpdir) / "concat.txt"

        for i, seg in enumerate(sequence):
            part_path = str(Path(tmpdir) / f"part_{i:03d}.wav")

            if seg.get("type") == "pause":
                generate_silence(seg["duration"], part_path)
            elif seg.get("voice") == "storyteller":
                generate_piper_audio(seg["text"], STORYTELLER_PIPER_MODEL, part_path)
            elif seg.get("voice") == "dog":
                generate_piper_audio(seg["text"], DOG_PIPER_MODEL, part_path)
            else:
                continue

            parts.append(f"file '{part_path}'")

        concat_list.write_text("\n".join(parts))

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:a",
            "pcm_s16le",
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)


def process_scripts(scripts_dir: str) -> None:
    """Generate two-voice audio for all script JSON files."""
    scripts_path = Path(scripts_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for script_file in sorted(scripts_path.glob("*_script.json")):
        print(f"[->] Generating voices: {script_file.name}")
        script = json.loads(script_file.read_text())

        sequence = build_audio_sequence(script)
        out_file = OUTPUT_DIR / f"{script_file.stem.replace('_script', '')}.wav"

        try:
            render_sequence(sequence, str(out_file))
            print(f"  [+] Audio saved: {out_file.name} ({len(sequence)} segments)")
        except Exception as e:
            print(f"  [x] Voice generation failed: {e}")


if __name__ == "__main__":
    scripts_dir = sys.argv[1] if len(sys.argv) > 1 else str(BASE_DIR / "output" / "scripts")
    process_scripts(scripts_dir)

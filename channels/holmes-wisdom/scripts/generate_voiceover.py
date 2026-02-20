#!/usr/bin/env python3
"""
Generate voiceover audio from Short scripts using Piper TTS.

Usage:
    python scripts/generate_voiceover.py [scripts_dir]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PIPER_MODEL = str(
    Path(__file__).parent.parent / "models" / "piper" / "voice-en-us-lessac-medium.onnx"
)

# ElevenLabs (optional upgrade)
USE_ELEVENLABS = False
ELEVENLABS_API_KEY = ""
ELEVENLABS_VOICE_ID = ""

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "audio"


def generate_with_piper(text: str, output_path: str) -> None:
    """Generate audio using local Piper TTS."""
    cmd = [
        "piper",
        "--model",
        PIPER_MODEL,
        "--output_file",
        output_path,
    ]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        raise RuntimeError(f"Piper failed: {stderr.decode()}")


def generate_with_elevenlabs(text: str, output_path: str) -> None:
    """Generate audio using ElevenLabs API (higher quality, costs money)."""
    import requests

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.75,
            "style": 0.3,
        },
    }
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)


def build_spoken_text(script: dict) -> str:
    """Combine hook + passage + closing into natural spoken text."""
    parts = []
    if script.get("hook"):
        parts.append(script["hook"])
    if script.get("passage"):
        parts.append(script["passage"])
    if script.get("closing"):
        parts.append(script["closing"])
    return " ... ".join(parts)


def process_scripts(scripts_dir: str, output_dir: str) -> None:
    """Generate voiceovers for all script JSON files."""
    scripts_path = Path(scripts_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generate_fn = generate_with_elevenlabs if USE_ELEVENLABS else generate_with_piper

    for script_file in sorted(scripts_path.glob("*_script.json")):
        print(f"[->] Generating voiceover: {script_file.name}")
        script = json.loads(script_file.read_text())
        spoken_text = build_spoken_text(script)

        out_file = output_path / f"{script_file.stem.replace('_script', '')}.wav"
        try:
            generate_fn(spoken_text, str(out_file))
            print(f"  [+] Audio saved: {out_file.name}")
        except Exception as e:
            print(f"  [x] TTS failed: {e}")


if __name__ == "__main__":
    scripts_dir = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(Path(__file__).parent.parent / "output" / "scripts")
    )
    process_scripts(scripts_dir, str(OUTPUT_DIR))

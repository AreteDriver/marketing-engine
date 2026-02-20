#!/usr/bin/env python3
"""
Research and generate scripts for rare instrument spotlight Shorts.
Uses Ollama to create engaging narration about forgotten instruments.

Usage:
    python scripts/extract_instrument.py "hurdy-gurdy"
    python scripts/extract_instrument.py --instruments-dir sources/instruments/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "audio"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are a passionate ethnomusicologist and storyteller who \
brings forgotten instruments to life. You make people HEAR an instrument \
through words alone, and you connect every instrument to the living culture \
that created it.

Your tone is warm, knowledgeable, and full of wonder — like a museum guide \
who genuinely loves what they're showing you. You use vivid sensory \
descriptions and surprising facts.

RULES:
1. The hook must make someone STOP scrolling — surprising fact or vivid sound
2. Describe the SOUND first, then the history
3. Connect to a specific culture, time, and place — not abstract "world music"
4. Include one genuinely surprising or little-known fact
5. Keep total spoken content to 100-140 words (40-60 second Short)

Respond ONLY in this JSON format:
{
    "instrument": "Full name of the instrument",
    "region": "Cultural origin",
    "era": "Historical period or 'contemporary'",
    "hook": "Scroll-stopping opening line",
    "sound_description": "Vivid description of what it sounds like",
    "cultural_context": "Where, when, and why this instrument mattered",
    "fun_fact": "One surprising fact most people don't know",
    "closing": "A thought-provoking or wistful closing line",
    "visual_cues": ["scene descriptions for visual generation"],
    "mood": "mystical|joyful|melancholic|powerful|meditative|playful",
    "related_instruments": ["similar or related instruments"],
    "estimated_duration_seconds": 50,
    "word_count": 120,
    "tags": ["tag1", "tag2", "tag3"]
}"""


def extract_instrument(instrument_name: str) -> dict:
    """Generate a Short script about a specific instrument."""
    payload = {
        "model": MODEL,
        "prompt": (
            f"Create a YouTube Short script about the {instrument_name}. "
            "Make the listener desperate to hear this instrument. "
            "JSON only."
        ),
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9},
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    raw = response.json()["response"]
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    return json.loads(raw.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Root Note Instrument Research")
    parser.add_argument("instrument", nargs="?", help="Instrument name")
    parser.add_argument("--instruments-dir", help="Process all instruments from directory")
    args = parser.parse_args()

    scripts_dir = BASE_DIR / "output" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    if args.instruments_dir:
        instruments_path = Path(args.instruments_dir)
        for instr_file in sorted(instruments_path.glob("*.txt")):
            instrument = instr_file.read_text().strip()
            print(f"[->] Researching: {instrument}")
            try:
                script = extract_instrument(instrument)
                out_file = scripts_dir / f"{instr_file.stem}_script.json"
                out_file.write_text(json.dumps(script, indent=2))
                print(f"  [+] Script: {out_file.name}")
                print(f"      Hook: {script['hook'][:60]}...")
            except Exception as e:
                print(f"  [x] Failed: {e}")
    elif args.instrument:
        print(f"[->] Researching: {args.instrument}")
        script = extract_instrument(args.instrument)
        slug = args.instrument.lower().replace(" ", "_").replace("-", "_")[:30]
        out_file = scripts_dir / f"{slug}_script.json"
        out_file.write_text(json.dumps(script, indent=2))
        print(f"[+] Script saved: {out_file}")
        print(json.dumps(script, indent=2))
    else:
        print("Usage: python extract_instrument.py 'instrument name'")
        sys.exit(1)


if __name__ == "__main__":
    main()

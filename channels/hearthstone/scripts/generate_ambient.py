#!/usr/bin/env python3
"""
Generate ambient soundscape configuration from a theme description.
Uses Ollama to design layered audio environments.

Usage:
    python scripts/generate_ambient.py "Rainy bookshop in Edinburgh"
    python scripts/generate_ambient.py --themes-dir sources/themes/
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

SYSTEM_PROMPT = """You are an ambient sound designer specializing in immersive \
environmental soundscapes. Given a theme, you design a layered audio environment \
with specific sound elements, their relative volumes, and how they change over time.

Design soundscapes that are:
- Deeply immersive and transportive
- Varied enough to avoid monotony over 8-12 hours
- Emotionally evocative without being distracting
- Suitable for study, sleep, work, or relaxation

Respond ONLY in this JSON format:
{
    "title": "Full descriptive title for the video",
    "theme": "The core theme",
    "duration_hours": 10,
    "layers": [
        {
            "name": "Layer name",
            "type": "ambient|nature|mechanical|music",
            "description": "What this sounds like",
            "volume": 0.7,
            "continuous": true,
            "variation": "How this layer changes over time"
        }
    ],
    "visual_mood": "Color palette and visual style description",
    "visual_elements": ["element1", "element2"],
    "tags": ["tag1", "tag2", "tag3"],
    "category": "urban|nature|fantasy|cultural|weather|cozy",
    "best_for": ["studying", "sleeping", "working"]
}"""


def generate_soundscape_config(theme: str) -> dict:
    """Generate a soundscape configuration from a theme."""
    payload = {
        "model": MODEL,
        "prompt": (
            f"Design an ambient soundscape for: {theme}\n\n"
            "Include 4-8 audio layers with specific descriptions. "
            "The soundscape should work for 8-12 hours without becoming repetitive."
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
    parser = argparse.ArgumentParser(description="Hearthstone Ambient Generator")
    parser.add_argument("theme", nargs="?", help="Theme description")
    parser.add_argument("--themes-dir", help="Process all themes from directory")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.themes_dir:
        themes_path = Path(args.themes_dir)
        for theme_file in sorted(themes_path.glob("*.txt")):
            theme = theme_file.read_text().strip()
            print(f"[->] Designing: {theme}")
            try:
                config = generate_soundscape_config(theme)
                out_file = OUTPUT_DIR / f"{theme_file.stem}_config.json"
                out_file.write_text(json.dumps(config, indent=2))
                print(f"  [+] Config: {out_file.name} ({len(config.get('layers', []))} layers)")
            except Exception as e:
                print(f"  [x] Failed: {e}")
    elif args.theme:
        print(f"[->] Designing: {args.theme}")
        config = generate_soundscape_config(args.theme)
        slug = args.theme.lower().replace(" ", "_")[:50]
        out_file = OUTPUT_DIR / f"{slug}_config.json"
        out_file.write_text(json.dumps(config, indent=2))
        print(f"[+] Config saved: {out_file}")
        print(json.dumps(config, indent=2))
    else:
        print("Usage: python generate_ambient.py 'theme description'")
        sys.exit(1)


if __name__ == "__main__":
    main()

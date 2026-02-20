#!/usr/bin/env python3
"""
Extract compelling passages from Ernest Holmes texts using Ollama.
Outputs structured JSON scripts for YouTube Shorts production.

Usage:
    python scripts/extract_passage.py <chunks_dir> <work_title>
    python scripts/extract_passage.py chunks/ "The Science of Mind"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are a content producer specializing in spiritual and \
philosophical YouTube Shorts. Your job is to extract the most powerful, \
compelling passages from Ernest Holmes' writings and transform them into \
30-45 second YouTube Short scripts.

RULES:
1. The passage must stand alone — no context needed
2. It must evoke emotion, insight, or a paradigm shift
3. Write a scroll-stopping hook (first 3 seconds) that is NOT from the source text
4. The hook should create curiosity or challenge a belief
5. Keep the total spoken word count between 75-120 words
6. End with a thought-provoking closing line (can be original)
7. Tag with relevant themes for visual matching

Respond ONLY in this JSON format:
{
    "hook": "The scroll-stopping opening line (your original words)",
    "passage": "The extracted Holmes passage (lightly adapted for spoken delivery)",
    "closing": "A punchy closing thought (can be original or from Holmes)",
    "themes": ["theme1", "theme2", "theme3"],
    "source_work": "Title of the source work",
    "mood": "contemplative|empowering|mystical|practical|challenging",
    "estimated_duration_seconds": 35,
    "word_count": 95
}"""

USER_PROMPT_TEMPLATE = """Here is a passage from Ernest Holmes' "{work_title}". \
Extract the most compelling segment and create a YouTube Short script from it.

---
{chunk_text}
---

Remember: JSON only. Hook must grab attention in 3 seconds. \
75-120 words total spoken content."""

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "scripts"


def extract_passage(chunk_text: str, work_title: str) -> dict:
    """Send chunk to Ollama and get structured Short script back."""
    payload = {
        "model": MODEL,
        "prompt": USER_PROMPT_TEMPLATE.format(
            work_title=work_title,
            chunk_text=chunk_text,
        ),
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    raw = response.json()["response"]

    # Parse JSON from response (handle markdown code blocks)
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    return json.loads(raw.strip())


def process_chunks(chunks_dir: str, output_dir: str, work_title: str) -> None:
    """Process all chunks in a directory."""
    chunks_path = Path(chunks_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for chunk_file in sorted(chunks_path.glob("*.txt")):
        print(f"[->] Processing: {chunk_file.name}")
        chunk_text = chunk_file.read_text()

        try:
            script = extract_passage(chunk_text, work_title)
            out_file = output_path / f"{chunk_file.stem}_script.json"
            out_file.write_text(json.dumps(script, indent=2))
            print(f"  [+] Script generated: {out_file.name}")
            print(f"      Hook: {script['hook'][:60]}...")
            print(f"      Mood: {script['mood']} | Words: {script.get('word_count', '?')}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [x] Failed to parse: {e}")
        except requests.RequestException as e:
            print(f"  [x] Ollama error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_passage.py <chunks_dir> <work_title>")
        print("Example: python extract_passage.py chunks/ 'The Science of Mind'")
        sys.exit(1)

    process_chunks(
        chunks_dir=sys.argv[1],
        output_dir=str(OUTPUT_DIR),
        work_title=sys.argv[2],
    )

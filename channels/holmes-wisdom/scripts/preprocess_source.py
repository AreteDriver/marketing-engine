#!/usr/bin/env python3
"""
Clean and chunk public domain texts for LLM processing.

Usage:
    python scripts/preprocess_source.py
"""

from __future__ import annotations

import re
from pathlib import Path

SOURCES_DIR = Path(__file__).parent.parent / "sources"
CHUNKS_DIR = Path(__file__).parent.parent / "chunks"


def clean_text(raw: str) -> str:
    """Remove OCR artifacts and normalize whitespace."""
    text = re.sub(r"[^\x00-\x7F]+", "", raw)  # strip non-ASCII OCR noise
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive newlines
    text = re.sub(r" {2,}", " ", text)  # collapse multiple spaces
    return text.strip()


def chunk_by_section(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into chunks roughly by paragraph groups."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars and current:
            chunks.append(current.strip())
            current = p
        else:
            current += "\n\n" + p
    if current.strip():
        chunks.append(current.strip())
    return chunks


def main() -> None:
    CHUNKS_DIR.mkdir(exist_ok=True)

    source_files = list(SOURCES_DIR.glob("*.txt"))
    if not source_files:
        print(f"No .txt files found in {SOURCES_DIR}")
        print("Download public domain texts and place them in sources/")
        return

    for txt_file in source_files:
        raw = txt_file.read_text(encoding="utf-8", errors="replace")
        cleaned = clean_text(raw)
        chunks = chunk_by_section(cleaned)
        for i, chunk in enumerate(chunks):
            out_path = CHUNKS_DIR / f"{txt_file.stem}_chunk_{i:03d}.txt"
            out_path.write_text(chunk)
        print(f"[+] {txt_file.name} -> {len(chunks)} chunks")


if __name__ == "__main__":
    main()

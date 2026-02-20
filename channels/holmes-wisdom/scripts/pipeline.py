#!/usr/bin/env python3
"""
Holmes Shorts Factory — Full Pipeline Orchestrator

Run the entire pipeline from source text to finished YouTube Shorts.

Usage:
    python scripts/pipeline.py                    # Process all chunks
    python scripts/pipeline.py --chunk 005        # Process single chunk
    python scripts/pipeline.py --batch 10         # Process N chunks
    python scripts/pipeline.py --step extract     # Run single step
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from assemble_short import assemble_short
from extract_passage import extract_passage
from generate_captions import generate_srt
from generate_visuals import MOOD_STYLE_MAP, STYLES, create_background_video
from generate_voiceover import build_spoken_text, generate_with_piper

BASE_DIR = Path(__file__).parent.parent


def run_pipeline(
    chunk_file: Path,
    work_title: str,
    music_file: str | None = None,
    steps: list[str] | None = None,
) -> bool:
    """Run full pipeline for a single chunk."""
    stem = chunk_file.stem
    all_steps = ["extract", "voiceover", "visuals", "captions", "assemble"]
    steps = steps or all_steps

    print(f"\n{'=' * 60}")
    print(f"Processing: {chunk_file.name}")
    print(f"{'=' * 60}")

    script_path = BASE_DIR / "output" / "scripts" / f"{stem}_script.json"
    audio_path = BASE_DIR / "output" / "audio" / f"{stem}.wav"
    visual_path = BASE_DIR / "output" / "visuals" / f"{stem}_bg.mp4"
    caption_path = BASE_DIR / "output" / "captions" / f"{stem}.srt"
    output_path = BASE_DIR / "output" / "shorts" / f"{stem}_short.mp4"

    for p in [script_path, audio_path, visual_path, caption_path, output_path]:
        p.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract passage
    if "extract" in steps:
        print("\n[1/5] Extracting passage...")
        chunk_text = chunk_file.read_text()
        try:
            script = extract_passage(chunk_text, work_title)
            script_path.write_text(json.dumps(script, indent=2))
            print(f"  Hook: {script['hook'][:80]}...")
        except Exception as e:
            print(f"  [x] Extraction failed: {e}")
            return False

    # Load script for remaining steps
    if not script_path.exists():
        print(f"  [!] No script found at {script_path}")
        return False
    script = json.loads(script_path.read_text())

    # Step 2: Generate voiceover
    if "voiceover" in steps:
        print("\n[2/5] Generating voiceover...")
        try:
            spoken_text = build_spoken_text(script)
            generate_with_piper(spoken_text, str(audio_path))
            print(f"  [+] Audio: {audio_path}")
        except Exception as e:
            print(f"  [x] TTS failed: {e}")
            return False

    # Step 3: Generate visuals
    if "visuals" in steps:
        print("\n[3/5] Generating visuals...")
        try:
            mood = script.get("mood", "contemplative")
            style_name = MOOD_STYLE_MAP.get(mood, "ethereal")
            style = STYLES[style_name]
            duration = script.get("estimated_duration_seconds", 35) + 3
            create_background_video(duration, style, str(visual_path))
            print(f"  [+] Visual: {visual_path} ({style_name})")
        except Exception as e:
            print(f"  [x] Visual generation failed: {e}")
            return False

    # Step 4: Generate captions
    if "captions" in steps:
        print("\n[4/5] Generating captions...")
        try:
            generate_srt(str(audio_path), str(caption_path))
            print(f"  [+] Captions: {caption_path}")
        except Exception as e:
            print(f"  [x] Caption generation failed: {e}")
            return False

    # Step 5: Assemble final Short
    if "assemble" in steps:
        print("\n[5/5] Assembling final Short...")
        try:
            assemble_short(
                str(visual_path),
                str(audio_path),
                str(caption_path),
                str(output_path),
                music_file=music_file,
            )
            print(f"\n  DONE: {output_path}")
        except Exception as e:
            print(f"  [x] Assembly failed: {e}")
            return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Holmes Shorts Factory")
    parser.add_argument(
        "--chunks-dir",
        default=str(BASE_DIR / "chunks"),
        help="Chunks directory",
    )
    parser.add_argument(
        "--work-title",
        default="The Science of Mind",
        help="Source work title",
    )
    parser.add_argument("--chunk", help="Process specific chunk number (e.g., 005)")
    parser.add_argument("--batch", type=int, help="Process N chunks")
    parser.add_argument(
        "--step",
        choices=["extract", "voiceover", "visuals", "captions", "assemble"],
        help="Run single step only",
    )
    parser.add_argument("--music", help="Path to background music file")
    args = parser.parse_args()

    chunks = sorted(Path(args.chunks_dir).glob("*.txt"))

    if args.chunk:
        chunks = [c for c in chunks if args.chunk in c.stem]
        if not chunks:
            print(f"No chunk matching '{args.chunk}' found")
            sys.exit(1)

    if args.batch:
        chunks = chunks[: args.batch]

    steps = [args.step] if args.step else None

    print("Holmes Shorts Factory")
    print(f"Chunks to process: {len(chunks)}")
    print(f"Steps: {steps or 'all'}")
    print(f"Work: {args.work_title}")

    success = 0
    for chunk in chunks:
        if run_pipeline(chunk, args.work_title, args.music, steps):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"Complete: {success}/{len(chunks)} Shorts generated")
    print(f"Output: {BASE_DIR / 'output' / 'shorts'}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Story Fire — Full Pipeline Orchestrator

Run the entire pipeline from folk tale source to finished YouTube Short.

Usage:
    python scripts/pipeline.py                          # Process all sources
    python scripts/pipeline.py --source grimm_001.txt   # Single tale
    python scripts/pipeline.py --batch 10               # Process N tales
    python scripts/pipeline.py --step extract           # Run single step
    python scripts/pipeline.py --culture norse           # Set culture
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assemble_short import assemble_short
from extract_tale import extract_tale
from generate_captions import generate_srt
from generate_visuals import CULTURE_PALETTES, create_background_video
from generate_voices import build_audio_sequence, render_sequence

BASE_DIR = Path(__file__).parent.parent


def run_pipeline(
    source_file: Path,
    culture: str,
    ambient_file: str | None = None,
    steps: list[str] | None = None,
) -> bool:
    """Run full pipeline for a single folk tale."""
    stem = source_file.stem
    all_steps = ["extract", "voices", "visuals", "captions", "assemble"]
    steps = steps or all_steps

    print(f"\n{'=' * 60}")
    print(f"Processing: {source_file.name} ({culture})")
    print(f"{'=' * 60}")

    script_path = BASE_DIR / "output" / "scripts" / f"{stem}_script.json"
    audio_path = BASE_DIR / "output" / "audio" / f"{stem}.wav"
    visual_path = BASE_DIR / "output" / "visuals" / f"{stem}_bg.mp4"
    caption_path = BASE_DIR / "output" / "captions" / f"{stem}.srt"
    output_path = BASE_DIR / "output" / "shorts" / f"{stem}_short.mp4"

    for p in [script_path, audio_path, visual_path, caption_path, output_path]:
        p.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract tale script (BARD)
    if "extract" in steps:
        print("\n[1/5] BARD — Extracting tale...")
        source_text = source_file.read_text()
        try:
            script = extract_tale(source_text, culture)
            script_path.write_text(json.dumps(script, indent=2))
            print(f"  Tale: {script.get('tale_title', '?')}")
            print(f"  Hook: {script['hook'][:80]}...")
            print(f"  Dog: {'Yes' if script.get('has_dog') else 'No'}")
        except Exception as e:
            print(f"  [x] Extraction failed: {e}")
            return False

    if not script_path.exists():
        print(f"  [!] No script found at {script_path}")
        return False
    script = json.loads(script_path.read_text())

    # Step 2: Generate two-voice narration (VOICE)
    if "voices" in steps:
        print("\n[2/5] VOICE — Generating narration...")
        try:
            sequence = build_audio_sequence(script)
            render_sequence(sequence, str(audio_path))
            print(f"  [+] Audio: {audio_path} ({len(sequence)} segments)")
        except Exception as e:
            print(f"  [x] Voice generation failed: {e}")
            return False

    # Step 3: Generate visuals (PAINTER)
    if "visuals" in steps:
        print("\n[3/5] PAINTER — Generating visuals...")
        try:
            script_culture = script.get("culture", culture).lower()
            for key in CULTURE_PALETTES:
                if key in script_culture:
                    script_culture = key
                    break
            else:
                script_culture = culture
            palette = CULTURE_PALETTES.get(script_culture, CULTURE_PALETTES["european"])
            duration = script.get("estimated_duration_seconds", 48) + 3
            create_background_video(duration, palette, str(visual_path))
            print(f"  [+] Visual: {visual_path} ({script_culture})")
        except Exception as e:
            print(f"  [x] Visual generation failed: {e}")
            return False

    # Step 4: Generate captions (SCRIBE)
    if "captions" in steps:
        print("\n[4/5] SCRIBE — Generating captions...")
        try:
            generate_srt(str(audio_path), str(caption_path))
            print(f"  [+] Captions: {caption_path}")
        except Exception as e:
            print(f"  [x] Caption generation failed: {e}")
            return False

    # Step 5: Assemble final Short (WEAVER)
    if "assemble" in steps:
        print("\n[5/5] WEAVER — Assembling final Short...")
        try:
            assemble_short(
                str(visual_path),
                str(audio_path),
                str(caption_path),
                str(output_path),
                ambient_file=ambient_file,
            )
            print(f"\n  DONE: {output_path}")
        except Exception as e:
            print(f"  [x] Assembly failed: {e}")
            return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Story Fire Pipeline")
    parser.add_argument(
        "--sources-dir",
        default=str(BASE_DIR / "sources"),
        help="Source tales directory",
    )
    parser.add_argument(
        "--culture",
        default="european",
        choices=[
            "european",
            "norse",
            "japanese",
            "african",
            "arabian",
            "celtic",
            "greek",
            "indian",
        ],
        help="Culture for tale extraction",
    )
    parser.add_argument("--source", help="Process specific source file")
    parser.add_argument("--batch", type=int, help="Process N tales")
    parser.add_argument(
        "--step",
        choices=["extract", "voices", "visuals", "captions", "assemble"],
        help="Run single step only",
    )
    parser.add_argument(
        "--ambient",
        default=str(BASE_DIR / "assets" / "audio" / "fire_crackle_loop.wav"),
        help="Path to ambient sound file",
    )
    args = parser.parse_args()

    sources = sorted(Path(args.sources_dir).glob("*.txt"))

    if args.source:
        sources = [s for s in sources if args.source in s.name]
        if not sources:
            print(f"No source matching '{args.source}' found")
            sys.exit(1)

    if args.batch:
        sources = sources[: args.batch]

    steps = [args.step] if args.step else None
    ambient = args.ambient if Path(args.ambient).exists() else None

    print("Story Fire Pipeline")
    print(f"Tales to process: {len(sources)}")
    print(f"Culture: {args.culture}")
    print(f"Steps: {steps or 'all'}")

    success = 0
    for source in sources:
        if run_pipeline(source, args.culture, ambient, steps):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"Complete: {success}/{len(sources)} Shorts generated")
    print(f"Output: {BASE_DIR / 'output' / 'shorts'}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

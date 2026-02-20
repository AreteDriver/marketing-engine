#!/usr/bin/env python3
"""
Root Note — Full Pipeline Orchestrator

Run the pipeline from instrument name to finished YouTube Short.

Usage:
    python scripts/pipeline.py --instrument "hurdy-gurdy"
    python scripts/pipeline.py --instruments-dir sources/instruments/ --batch 10
    python scripts/pipeline.py --step extract --instrument "kora"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_instrument import extract_instrument

BASE_DIR = Path(__file__).parent.parent


def generate_voiceover(text: str, output_path: str, piper_model: str) -> None:
    """Generate voiceover using Piper TTS."""
    cmd = ["piper", "--model", piper_model, "--output_file", output_path]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _, stderr = process.communicate(input=text.encode("utf-8"))
    if process.returncode != 0:
        raise RuntimeError(f"Piper failed: {stderr.decode()}")


def generate_captions(audio_path: str, output_path: str) -> None:
    """Generate SRT captions using Whisper."""
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True, language="en")

    words = []
    for segment in result["segments"]:
        if "words" in segment:
            words.extend(segment["words"])

    srt_entries = []
    idx = 1
    for i in range(0, len(words), 4):
        group = words[i : i + 4]
        start = group[0]["start"]
        end = group[-1]["end"]
        text = " ".join(w["word"].strip() for w in group)
        h, m, s = int(start // 3600), int((start % 3600) // 60), start % 60
        eh, em, es = int(end // 3600), int((end % 3600) // 60), end % 60
        srt_entries.append(
            f"{idx}\n{h:02d}:{m:02d}:{s:06.3f} --> {eh:02d}:{em:02d}:{es:06.3f}\n{text}\n"
        )
        idx += 1

    Path(output_path).write_text("\n".join(srt_entries))


def run_pipeline(
    instrument: str,
    steps: list[str] | None = None,
) -> bool:
    """Run full pipeline for a single instrument."""
    all_steps = ["extract", "voiceover", "visuals", "captions", "assemble"]
    steps = steps or all_steps

    slug = instrument.lower().replace(" ", "_").replace("-", "_")[:30]

    print(f"\n{'=' * 60}")
    print(f"Processing: {instrument}")
    print(f"{'=' * 60}")

    script_path = BASE_DIR / "output" / "scripts" / f"{slug}_script.json"
    audio_path = BASE_DIR / "output" / "audio" / f"{slug}.wav"
    visual_path = BASE_DIR / "output" / "visuals" / f"{slug}_bg.mp4"
    caption_path = BASE_DIR / "output" / "audio" / f"{slug}.srt"
    output_path = BASE_DIR / "output" / "videos" / f"{slug}_short.mp4"

    for p in [script_path, audio_path, visual_path, caption_path, output_path]:
        p.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract instrument script
    if "extract" in steps:
        print("\n[1/5] Researching instrument...")
        try:
            script = extract_instrument(instrument)
            script_path.write_text(json.dumps(script, indent=2))
            print(f"  Hook: {script['hook'][:80]}...")
        except Exception as e:
            print(f"  [x] Research failed: {e}")
            return False

    if not script_path.exists():
        print(f"  [!] No script at {script_path}")
        return False
    script = json.loads(script_path.read_text())

    # Step 2: Generate voiceover
    if "voiceover" in steps:
        print("\n[2/5] Generating voiceover...")
        spoken = " ... ".join(
            filter(
                None,
                [
                    script.get("hook"),
                    script.get("sound_description"),
                    script.get("cultural_context"),
                    script.get("fun_fact"),
                    script.get("closing"),
                ],
            )
        )
        piper_model = str(BASE_DIR / "models" / "piper" / "voice-en-us-lessac-medium.onnx")
        try:
            generate_voiceover(spoken, str(audio_path), piper_model)
            print(f"  [+] Audio: {audio_path}")
        except Exception as e:
            print(f"  [x] TTS failed: {e}")
            return False

    # Step 3: Generate visuals (gradient placeholder)
    if "visuals" in steps:
        print("\n[3/5] Generating visuals...")
        duration = script.get("estimated_duration_seconds", 50) + 3
        try:
            bg_img = tempfile.mktemp(suffix=".png")
            subprocess.run(
                [
                    "magick",
                    "-size",
                    "1080x1920",
                    "gradient:#1a1008-#2c1810",
                    bg_img,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    bg_img,
                    "-t",
                    str(duration),
                    "-vf",
                    (
                        "scale=1200:2133,"
                        "zoompan=z='min(zoom+0.0005,1.1)':"
                        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={int(duration * 30)}:s=1080x1920:fps=30"
                    ),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(visual_path),
                ],
                check=True,
                capture_output=True,
            )
            print(f"  [+] Visual: {visual_path}")
        except subprocess.CalledProcessError as e:
            print(f"  [x] Visual generation failed: {e}")
            return False

    # Step 4: Generate captions
    if "captions" in steps:
        print("\n[4/5] Generating captions...")
        try:
            generate_captions(str(audio_path), str(caption_path))
            print(f"  [+] Captions: {caption_path}")
        except Exception as e:
            print(f"  [x] Captions failed: {e}")
            return False

    # Step 5: Assemble
    if "assemble" in steps:
        print("\n[5/5] Assembling Short...")
        try:
            probe = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ]
            )
            duration = float(probe.decode().strip()) + 1.5

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(visual_path),
                    "-i",
                    str(audio_path),
                    "-t",
                    str(duration),
                    "-filter_complex",
                    (
                        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
                        f"subtitles={caption_path}[vout]"
                    ),
                    "-map",
                    "[vout]",
                    "-map",
                    "1:a",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
            )
            print(f"\n  DONE: {output_path}")
        except Exception as e:
            print(f"  [x] Assembly failed: {e}")
            return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Root Note Pipeline")
    parser.add_argument("--instrument", help="Instrument name")
    parser.add_argument("--instruments-dir", help="Directory with instrument files")
    parser.add_argument("--batch", type=int, help="Process N instruments")
    parser.add_argument(
        "--step",
        choices=["extract", "voiceover", "visuals", "captions", "assemble"],
        help="Run single step",
    )
    args = parser.parse_args()

    steps = [args.step] if args.step else None

    if args.instruments_dir:
        instruments = [
            f.read_text().strip() for f in sorted(Path(args.instruments_dir).glob("*.txt"))
        ]
        if args.batch:
            instruments = instruments[: args.batch]
    elif args.instrument:
        instruments = [args.instrument]
    else:
        print("Provide --instrument or --instruments-dir")
        sys.exit(1)

    print("Root Note Pipeline")
    print(f"Instruments: {len(instruments)}")

    success = 0
    for instrument in instruments:
        if run_pipeline(instrument, steps):
            success += 1

    print(f"\n{'=' * 60}")
    print(f"Complete: {success}/{len(instruments)} Shorts generated")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

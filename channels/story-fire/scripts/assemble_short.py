#!/usr/bin/env python3
"""
WEAVER Agent — Assemble final Story Fire YouTube Short from components.
Combines: culture-matched background + two-voice narration + captions + ambient.
Output: 1080x1920 MP4 ready for YouTube upload.

Usage:
    python scripts/assemble_short.py [ambient_file]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Caption styling — serif-inspired for storytelling aesthetic
CAPTION_STYLE = (
    "FontName=Impact,"
    "FontSize=22,"
    "PrimaryColour=&H00F5DEB3,"
    "OutlineColour=&H00000000,"
    "BorderStyle=3,"
    "BackColour=&H80000000,"
    "Outline=2,"
    "Shadow=0,"
    "MarginV=120,"
    "Alignment=2"
)

AMBIENT_VOLUME = 0.08


def assemble_short(
    background_video: str,
    audio_file: str,
    caption_file: str,
    output_file: str,
    ambient_file: str | None = None,
) -> None:
    """Assemble all components into a final Short."""
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_file,
    ]
    duration = float(subprocess.check_output(probe_cmd).decode().strip())
    duration += 1.5

    inputs = ["-i", background_video, "-i", audio_file]
    filter_parts = []
    audio_mix = "[1:a]"

    if ambient_file and Path(ambient_file).exists():
        inputs.extend(["-i", ambient_file])
        filter_parts.append(
            f"[2:a]volume={AMBIENT_VOLUME}[ambient];"
            f"[1:a][ambient]amix=inputs=2:duration=first[mixed]"
        )
        audio_mix = "[mixed]"

    sub_filter = f"subtitles={caption_file}:force_style='{CAPTION_STYLE}'"

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-t",
        str(duration),
        "-filter_complex",
        (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"{sub_filter}[vout];" + ("".join(filter_parts) if filter_parts else "")
        ).rstrip(";"),
        "-map",
        "[vout]",
        "-map",
        audio_mix,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        output_file,
    ]

    print(f"[->] Assembling: {output_file}")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[+] Done! Duration: {duration:.1f}s")


def process_all(ambient_file: str | None = None) -> None:
    """Assemble all Shorts from generated components."""
    scripts_dir = BASE_DIR / "output" / "scripts"
    audio_dir = BASE_DIR / "output" / "audio"
    visuals_dir = BASE_DIR / "output" / "visuals"
    captions_dir = BASE_DIR / "output" / "captions"
    output_dir = BASE_DIR / "output" / "shorts"
    output_dir.mkdir(parents=True, exist_ok=True)

    for script_file in sorted(scripts_dir.glob("*_script.json")):
        stem = script_file.stem.replace("_script", "")
        audio = audio_dir / f"{stem}.wav"
        visual = visuals_dir / f"{stem}_bg.mp4"
        caption = captions_dir / f"{stem}.srt"
        output = output_dir / f"{stem}_short.mp4"

        if not audio.exists():
            print(f"  [!] Missing audio: {audio}")
            continue
        if not visual.exists():
            print(f"  [!] Missing visual: {visual}")
            continue
        if not caption.exists():
            print(f"  [!] Missing caption: {caption}")
            continue

        try:
            assemble_short(
                str(visual),
                str(audio),
                str(caption),
                str(output),
                ambient_file=ambient_file,
            )
        except subprocess.CalledProcessError as e:
            print(f"  [x] Assembly failed for {stem}: {e}")


if __name__ == "__main__":
    ambient = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(BASE_DIR / "assets" / "audio" / "fire_crackle_loop.wav")
    )
    if not Path(ambient).exists():
        ambient = None
    process_all(ambient_file=ambient)

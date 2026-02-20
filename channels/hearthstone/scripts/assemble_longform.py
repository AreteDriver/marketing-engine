#!/usr/bin/env python3
"""
Assemble long-form ambient video from audio layers and visual loops.

Takes a soundscape config JSON and produces an 8-12 hour video
with seamlessly looped audio and subtle motion visuals.

Usage:
    python scripts/assemble_longform.py <config.json> [--duration 10]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "videos"


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    return float(subprocess.check_output(cmd).decode().strip())


def loop_audio(input_path: str, output_path: str, target_duration_hours: float) -> None:
    """Loop an audio file to reach target duration."""
    target_seconds = target_duration_hours * 3600

    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        input_path,
        "-t",
        str(target_seconds),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def create_visual_loop(
    visual_path: str,
    output_path: str,
    duration_hours: float,
    width: int = 1920,
    height: int = 1080,
) -> None:
    """Create a long visual loop with subtle Ken Burns effect."""
    duration_seconds = duration_hours * 3600

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        visual_path,
        "-t",
        str(duration_seconds),
        "-vf",
        (
            f"scale=2100:1181,zoompan=z='1+0.0003*sin(2*PI*on/(30*120))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={int(duration_seconds * 30)}:s={width}x{height}:fps=30"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def assemble_video(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> None:
    """Combine video and audio into final output."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hearthstone Long-form Assembler")
    parser.add_argument("config", help="Soundscape config JSON file")
    parser.add_argument("--audio", help="Pre-mixed audio file to use")
    parser.add_argument("--visual", help="Background image for visual loop")
    parser.add_argument("--duration", type=float, default=10, help="Duration in hours")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text())
    title = config.get("title", "ambient")
    slug = title.lower().replace(" ", "_")[:60]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.audio:
        print("[!] --audio required: provide a pre-mixed ambient audio file")
        print("    (Use Suno/Udio to generate, or mix layers manually)")
        sys.exit(1)

    if not args.visual:
        print("[!] --visual required: provide a background image")
        print("    (Use Stable Diffusion or stock imagery)")
        sys.exit(1)

    print(f"[->] Assembling: {title} ({args.duration}h)")

    # Step 1: Loop audio
    looped_audio = str(OUTPUT_DIR / f"{slug}_audio.m4a")
    print(f"  [1/3] Looping audio to {args.duration}h...")
    loop_audio(args.audio, looped_audio, args.duration)

    # Step 2: Create visual loop
    visual_loop = str(OUTPUT_DIR / f"{slug}_visual.mp4")
    print(f"  [2/3] Creating visual loop ({args.duration}h)...")
    create_visual_loop(args.visual, visual_loop, args.duration)

    # Step 3: Assemble final video
    final_output = str(OUTPUT_DIR / f"{slug}.mp4")
    print("  [3/3] Assembling final video...")
    assemble_video(visual_loop, looped_audio, final_output)

    print(f"\n[+] Done: {final_output}")
    print(f"    Duration: {args.duration}h")
    print(f"    Title: {title}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate background visuals for Holmes Wisdom Shorts.

MVP: Gradient backgrounds with subtle zoom animation.
V2: Stable Diffusion generated imagery based on themes.

Usage:
    python scripts/generate_visuals.py [scripts_dir]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Visual style presets — mood-matched gradients
STYLES = {
    "cosmic": {
        "gradient_start": "#0a0a2e",
        "gradient_end": "#1a0533",
        "text_color": "#e8d5b7",
        "accent_color": "#7b68ee",
    },
    "vintage": {
        "gradient_start": "#2c1810",
        "gradient_end": "#1a1008",
        "text_color": "#d4a574",
        "accent_color": "#8b6914",
    },
    "ethereal": {
        "gradient_start": "#0d1b2a",
        "gradient_end": "#1b263b",
        "text_color": "#e0e1dd",
        "accent_color": "#778da9",
    },
    "empowering": {
        "gradient_start": "#1a1a2e",
        "gradient_end": "#16213e",
        "text_color": "#f4d03f",
        "accent_color": "#e74c3c",
    },
}

MOOD_STYLE_MAP = {
    "contemplative": "ethereal",
    "empowering": "empowering",
    "mystical": "cosmic",
    "practical": "vintage",
    "challenging": "empowering",
}

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visuals"


def create_gradient_background(width: int, height: int, style: dict, output_path: str) -> None:
    """Create a gradient background image using ImageMagick."""
    cmd = [
        "magick",
        "-size",
        f"{width}x{height}",
        f"gradient:{style['gradient_start']}-{style['gradient_end']}",
        output_path,
    ]
    subprocess.run(cmd, check=True)


def create_background_video(
    duration: float,
    style: dict,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
) -> None:
    """Create an animated gradient background video with subtle zoom."""
    bg_img = "/tmp/holmes_bg.png"
    create_gradient_background(width, height, style, bg_img)

    cmd = [
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
            f"scale=1200:2133,zoompan=z='min(zoom+0.0005,1.1)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={int(duration * 30)}:s={width}x{height}:fps=30"
        ),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def process_scripts(scripts_dir: str, output_dir: str) -> None:
    """Generate background videos for all scripts."""
    scripts_path = Path(scripts_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for script_file in sorted(scripts_path.glob("*_script.json")):
        print(f"[->] Generating visual: {script_file.name}")
        script = json.loads(script_file.read_text())

        mood = script.get("mood", "contemplative")
        style_name = MOOD_STYLE_MAP.get(mood, "ethereal")
        style = STYLES[style_name]
        duration = script.get("estimated_duration_seconds", 35) + 3

        out_file = output_path / f"{script_file.stem.replace('_script', '')}_bg.mp4"
        try:
            create_background_video(duration, style, str(out_file))
            print(f"  [+] Visual saved: {out_file.name} ({style_name})")
        except subprocess.CalledProcessError as e:
            print(f"  [x] Visual generation failed: {e}")


if __name__ == "__main__":
    scripts_dir = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(Path(__file__).parent.parent / "output" / "scripts")
    )
    process_scripts(scripts_dir, str(OUTPUT_DIR))

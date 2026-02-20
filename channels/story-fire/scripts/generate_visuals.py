#!/usr/bin/env python3
"""
PAINTER Agent — Culture-specific visual generation for Story Fire.

MVP: Gradient backgrounds matching culture palette with subtle animation.
V2: Stable Diffusion with culture-specific art style prompts.

Usage:
    python scripts/generate_visuals.py [scripts_dir]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "visuals"

# Culture-specific visual palettes
CULTURE_PALETTES = {
    "european": {
        "colors": ["#8B6914", "#2C1810", "#D4A574", "#1A1008", "#C9956B"],
        "gradient_start": "#2C1810",
        "gradient_end": "#1A1008",
        "sd_style": (
            "oil painting, medieval illuminated manuscript style, "
            "golden candlelight, rich shadows, warm amber tones, "
            "detailed brushwork, fairy tale illustration, "
            "Arthur Rackham inspired, Brian Froud inspired"
        ),
    },
    "norse": {
        "colors": ["#1B3A4B", "#8B6914", "#C0C0C0", "#0A1628", "#4A6741"],
        "gradient_start": "#0A1628",
        "gradient_end": "#1B3A4B",
        "sd_style": (
            "oil painting, viking age art style, carved wood texture, "
            "frost and firelight, deep blue and amber, "
            "runic borders, aurora borealis glow, stark and powerful"
        ),
    },
    "japanese": {
        "colors": ["#2D1B2E", "#D4A574", "#8B4513", "#F5F5DC", "#9B2335"],
        "gradient_start": "#2D1B2E",
        "gradient_end": "#1A0A1B",
        "sd_style": (
            "ukiyo-e woodblock print style, atmospheric mist, "
            "ink wash painting, soft moonlight, cherry blossom pink, "
            "paper lantern glow, delicate linework, wabi-sabi aesthetic"
        ),
    },
    "african": {
        "colors": ["#8B4513", "#D2691E", "#DAA520", "#2F1810", "#CD853F"],
        "gradient_start": "#2F1810",
        "gradient_end": "#8B4513",
        "sd_style": (
            "warm earth tones, bold geometric patterns, "
            "sunset savanna light, rich ochre and sienna, "
            "carved wood texture, starlit sky, tribal art inspired, "
            "powerful silhouettes against golden sky"
        ),
    },
    "arabian": {
        "colors": ["#1A237E", "#DAA520", "#800020", "#0D1117", "#C0965C"],
        "gradient_start": "#0D1117",
        "gradient_end": "#1A237E",
        "sd_style": (
            "persian miniature painting style, intricate geometric patterns, "
            "lapis lazuli blue and gold leaf, oil lamp warmth, "
            "palace courtyard moonlight, arabesque borders, "
            "rich jewel tones, desert night sky"
        ),
    },
    "celtic": {
        "colors": ["#2E5339", "#8B6914", "#4A6741", "#1A1008", "#A0785A"],
        "gradient_start": "#1A1008",
        "gradient_end": "#2E5339",
        "sd_style": (
            "celtic knotwork borders, misty green hills, "
            "ancient stone circles, bog and heather, "
            "moonlit standing stones, watercolor style, "
            "fairy ring glow, manuscript illumination"
        ),
    },
    "greek": {
        "colors": ["#C2452D", "#1A1A2E", "#DAA520", "#F5F5DC", "#4169E1"],
        "gradient_start": "#1A1A2E",
        "gradient_end": "#C2452D",
        "sd_style": (
            "ancient greek pottery art style, black figure and red figure, "
            "mediterranean light, marble and olive groves, "
            "heroic poses, laurel wreaths, temple columns"
        ),
    },
    "indian": {
        "colors": ["#FF6347", "#DAA520", "#800080", "#006400", "#F5F5DC"],
        "gradient_start": "#2A0A1A",
        "gradient_end": "#800080",
        "sd_style": (
            "Mughal miniature painting style, vibrant jewel tones, "
            "intricate floral borders, palace scenes, "
            "lotus and peacock motifs, warm golden light"
        ),
    },
}

# Mood modifiers for Stable Diffusion prompts
MOOD_MODIFIERS = {
    "warm_dark": "intimate firelight, deep rich shadows, warm and foreboding",
    "whimsical": "magical sparkle, enchanted glow, playful light",
    "haunting": "eerie mist, pale moonlight, unsettling beauty",
    "triumphant": "golden dawn light, heroic composition, soaring feeling",
    "bittersweet": "fading autumn light, beautiful melancholy, gentle sadness",
    "terrifying_but_wry": "dark humor, grotesque beauty, candlelit horror",
}


def build_visual_prompt(scene: str, culture: str, mood: str) -> tuple[str, str]:
    """Build Stable Diffusion prompt for a specific scene."""
    palette = CULTURE_PALETTES.get(culture, CULTURE_PALETTES["european"])
    base = palette["sd_style"]
    mood_mod = MOOD_MODIFIERS.get(mood, "warm firelight")

    prompt = (
        f"{scene}, {base}, {mood_mod}, "
        f"storytelling illustration, painterly, atmospheric, "
        f"no text, no words, no letters, no UI, "
        f"masterpiece, best quality, highly detailed"
    )

    negative = (
        "text, words, letters, watermark, signature, "
        "photorealistic, photograph, 3d render, "
        "modern, contemporary, cartoon, anime, chibi, "
        "blurry, low quality, deformed, ugly"
    )

    return prompt, negative


def create_gradient_background(width: int, height: int, palette: dict, output_path: str) -> None:
    """Create a gradient background using ImageMagick."""
    cmd = [
        "magick",
        "-size",
        f"{width}x{height}",
        f"gradient:{palette['gradient_start']}-{palette['gradient_end']}",
        output_path,
    ]
    subprocess.run(cmd, check=True)


def create_background_video(
    duration: float,
    palette: dict,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
) -> None:
    """Create animated gradient background video with Ken Burns zoom."""
    bg_img = "/tmp/storyfire_bg.png"
    create_gradient_background(width, height, palette, bg_img)

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


def process_scripts(scripts_dir: str) -> None:
    """Generate culture-matched visuals for all scripts."""
    scripts_path = Path(scripts_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for script_file in sorted(scripts_path.glob("*_script.json")):
        print(f"[->] Generating visual: {script_file.name}")
        script = json.loads(script_file.read_text())

        culture = script.get("culture", "european").lower()
        # Normalize culture names
        for key in CULTURE_PALETTES:
            if key in culture:
                culture = key
                break
        else:
            culture = "european"

        palette = CULTURE_PALETTES[culture]
        duration = script.get("estimated_duration_seconds", 48) + 3

        out_file = OUTPUT_DIR / f"{script_file.stem.replace('_script', '')}_bg.mp4"
        try:
            create_background_video(duration, palette, str(out_file))
            print(f"  [+] Visual saved: {out_file.name} ({culture})")
        except subprocess.CalledProcessError as e:
            print(f"  [x] Visual generation failed: {e}")


if __name__ == "__main__":
    scripts_dir = sys.argv[1] if len(sys.argv) > 1 else str(BASE_DIR / "output" / "scripts")
    process_scripts(scripts_dir)

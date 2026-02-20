"""FFmpeg-based Short composer."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from timeless_clips.models import ShortScript

logger = logging.getLogger(__name__)

COLOR_PRESETS = {
    "warm_vintage": "colorbalance=rs=0.1:gs=-0.05:bs=-0.15",
    "high_contrast_bw": ("colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,eq=contrast=1.3"),
    "sepia": ("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"),
    "technicolor": ("eq=saturation=1.5:contrast=1.1,colorbalance=rs=0.1:bs=-0.1"),
    "noir": ("colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3,eq=contrast=1.5:brightness=-0.05"),
}


class ShortComposer:
    """Compose a final vertical Short from source clip + narration + captions."""

    def __init__(self, config: dict) -> None:
        output_config = config.get("output", {})
        visual_config = config.get("visuals", {})
        self._resolution = output_config.get("resolution", "1080x1920")
        self._max_duration = output_config.get("max_duration", 60)
        self._codec = output_config.get("codec", "libx264")
        self._crf = output_config.get("crf", 23)
        self._color_preset = visual_config.get("default_color_preset", "warm_vintage")

    def compose(
        self,
        script: ShortScript,
        source_path: Path,
        narration_path: Path,
        caption_path: Path,
        output_path: Path,
    ) -> Path:
        """Compose the final MP4 Short."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_command(script, source_path, narration_path, caption_path, output_path)
        logger.info("Running FFmpeg: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
        return output_path

    def _build_command(
        self,
        script: ShortScript,
        source_path: Path,
        narration_path: Path,
        caption_path: Path,
        output_path: Path,
    ) -> list[str]:
        """Build the FFmpeg command line."""
        width, height = self._resolution.split("x")
        duration = min(script.duration, self._max_duration)
        color_filter = COLOR_PRESETS.get(self._color_preset, "")

        # Video filter chain
        vf_parts = [
            f"crop=ih*{width}/{height}:ih",  # Center crop to 9:16
            f"scale={width}:{height}",
        ]
        if color_filter:
            vf_parts.append(color_filter)
        # Burn in captions
        vf_parts.append(
            f"subtitles={caption_path}:force_style="
            "'FontSize=18,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,Alignment=2'"
        )
        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(script.start_time),
            "-t",
            str(duration),
            "-i",
            str(source_path),
            "-i",
            str(narration_path),
            "-filter_complex",
            "[0:a]volume=0.3[bg];[1:a]volume=1.0[narr];[bg][narr]amix=inputs=2[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-vf",
            vf,
            "-c:v",
            self._codec,
            "-crf",
            str(self._crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        return cmd

    def build_command(
        self,
        script: ShortScript,
        source_path: Path,
        narration_path: Path,
        caption_path: Path,
        output_path: Path,
    ) -> list[str]:
        """Public access to the command builder (for dry-run inspection)."""
        return self._build_command(script, source_path, narration_path, caption_path, output_path)

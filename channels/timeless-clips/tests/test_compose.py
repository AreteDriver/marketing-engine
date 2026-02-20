"""Tests for timeless_clips.compose — ShortComposer and COLOR_PRESETS."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from timeless_clips.compose import COLOR_PRESETS, ShortComposer
from timeless_clips.models import ShortScript, TextOverlay


def _make_script(
    *,
    start_time: float = 10.0,
    end_time: float = 40.0,
    item_id: str = "test-clip",
) -> ShortScript:
    """Helper to create a ShortScript with sensible defaults."""
    return ShortScript(
        item_id=item_id,
        hook="You won't believe this",
        start_time=start_time,
        end_time=end_time,
        narration="Narration text here.",
        text_overlays=[TextOverlay(time=2.0, text="1951")],
        closing="Follow for more.",
        category="educational",
        mood="nostalgic",
        tags=["test"],
    )


class TestColorPresets:
    """Tests for the COLOR_PRESETS dictionary."""

    def test_presets_has_five_entries(self) -> None:
        assert len(COLOR_PRESETS) == 5

    def test_preset_keys(self) -> None:
        expected = {"warm_vintage", "high_contrast_bw", "sepia", "technicolor", "noir"}
        assert set(COLOR_PRESETS.keys()) == expected

    def test_all_presets_are_nonempty_strings(self) -> None:
        for name, value in COLOR_PRESETS.items():
            assert isinstance(value, str), f"{name} should be a string"
            assert len(value) > 0, f"{name} should not be empty"


class TestShortComposerInit:
    """Tests for ShortComposer construction and config parsing."""

    def test_default_config(self) -> None:
        composer = ShortComposer({})
        assert composer._resolution == "1080x1920"
        assert composer._max_duration == 60
        assert composer._codec == "libx264"
        assert composer._crf == 23
        assert composer._color_preset == "warm_vintage"

    def test_custom_resolution(self) -> None:
        config = {"output": {"resolution": "720x1280"}}
        composer = ShortComposer(config)
        assert composer._resolution == "720x1280"

    def test_custom_codec(self) -> None:
        config = {"output": {"codec": "libx265"}}
        composer = ShortComposer(config)
        assert composer._codec == "libx265"

    def test_custom_crf(self) -> None:
        config = {"output": {"crf": 18}}
        composer = ShortComposer(config)
        assert composer._crf == 18

    def test_custom_max_duration(self) -> None:
        config = {"output": {"max_duration": 45}}
        composer = ShortComposer(config)
        assert composer._max_duration == 45

    def test_custom_color_preset(self) -> None:
        config = {"visuals": {"default_color_preset": "noir"}}
        composer = ShortComposer(config)
        assert composer._color_preset == "noir"


class TestBuildCommand:
    """Tests for ShortComposer._build_command / build_command."""

    @pytest.fixture()
    def composer(self) -> ShortComposer:
        return ShortComposer(
            {
                "output": {
                    "resolution": "1080x1920",
                    "max_duration": 60,
                    "codec": "libx264",
                    "crf": 23,
                },
                "visuals": {"default_color_preset": "warm_vintage"},
            }
        )

    @pytest.fixture()
    def paths(self, tmp_path: Path) -> dict[str, Path]:
        return {
            "source": tmp_path / "source.mp4",
            "narration": tmp_path / "narration.wav",
            "caption": tmp_path / "captions.srt",
            "output": tmp_path / "output" / "final.mp4",
        }

    def test_command_starts_with_ffmpeg(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert cmd[0] == "ffmpeg"

    def test_command_has_overwrite_flag(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert "-y" in cmd

    def test_command_has_start_time(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script(start_time=15.0)
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        ss_idx = cmd.index("-ss")
        assert cmd[ss_idx + 1] == "15.0"

    def test_command_has_duration(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script(start_time=10.0, end_time=40.0)
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "30.0"

    def test_duration_capped_at_max_duration(self, paths: dict) -> None:
        composer = ShortComposer({"output": {"max_duration": 20}})
        script = _make_script(start_time=0.0, end_time=50.0)  # 50s > 20s cap
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "20"

    def test_resolution_in_scale_filter(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert "scale=1080:1920" in vf_value

    def test_color_preset_in_vf_chain(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert COLOR_PRESETS["warm_vintage"] in vf_value

    def test_unknown_color_preset_no_color_filter(self, paths: dict) -> None:
        composer = ShortComposer({"visuals": {"default_color_preset": "nonexistent_preset"}})
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        # Should not contain any color preset filter strings
        for preset_filter in COLOR_PRESETS.values():
            assert preset_filter not in vf_value

    def test_caption_path_in_subtitles_filter(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert f"subtitles={paths['caption']}" in vf_value

    def test_codec_in_command(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        cv_idx = cmd.index("-c:v")
        assert cmd[cv_idx + 1] == "libx264"

    def test_crf_in_command(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        crf_idx = cmd.index("-crf")
        assert cmd[crf_idx + 1] == "23"

    def test_output_path_is_last_arg(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert cmd[-1] == str(paths["output"])

    def test_audio_mixing_filter(self, composer: ShortComposer, paths: dict) -> None:
        script = _make_script()
        cmd = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        fc_idx = cmd.index("-filter_complex")
        fc_value = cmd[fc_idx + 1]
        assert "amix=inputs=2" in fc_value
        assert "volume=0.3" in fc_value
        assert "volume=1.0" in fc_value

    def test_public_build_command_matches_private(
        self, composer: ShortComposer, paths: dict
    ) -> None:
        script = _make_script()
        public = composer.build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        private = composer._build_command(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert public == private


class TestCompose:
    """Tests for ShortComposer.compose (subprocess execution)."""

    @pytest.fixture()
    def composer(self) -> ShortComposer:
        return ShortComposer({})

    @pytest.fixture()
    def paths(self, tmp_path: Path) -> dict[str, Path]:
        return {
            "source": tmp_path / "source.mp4",
            "narration": tmp_path / "narration.wav",
            "caption": tmp_path / "captions.srt",
            "output": tmp_path / "output" / "final.mp4",
        }

    @patch("timeless_clips.compose.subprocess.run")
    def test_compose_success_returns_output_path(
        self, mock_run: MagicMock, composer: ShortComposer, paths: dict
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        script = _make_script()
        result = composer.compose(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert result == paths["output"]

    @patch("timeless_clips.compose.subprocess.run")
    def test_compose_creates_output_directory(
        self, mock_run: MagicMock, composer: ShortComposer, paths: dict
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        script = _make_script()
        composer.compose(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        assert paths["output"].parent.exists()

    @patch("timeless_clips.compose.subprocess.run")
    def test_compose_calls_subprocess(
        self, mock_run: MagicMock, composer: ShortComposer, paths: dict
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        script = _make_script()
        composer.compose(
            script, paths["source"], paths["narration"], paths["caption"], paths["output"]
        )
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["timeout"] == 300

    @patch("timeless_clips.compose.subprocess.run")
    def test_compose_failure_raises_runtime_error(
        self, mock_run: MagicMock, composer: ShortComposer, paths: dict
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="Error: codec not found")
        script = _make_script()
        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            composer.compose(
                script, paths["source"], paths["narration"], paths["caption"], paths["output"]
            )

    @patch("timeless_clips.compose.subprocess.run")
    def test_compose_failure_includes_stderr(
        self, mock_run: MagicMock, composer: ShortComposer, paths: dict
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="specific error message")
        script = _make_script()
        with pytest.raises(RuntimeError, match="specific error message"):
            composer.compose(
                script, paths["source"], paths["narration"], paths["caption"], paths["output"]
            )

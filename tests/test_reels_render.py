import os
import tempfile
from pathlib import Path

import pytest


def _ffmpeg_bin():
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _run(cmd: list[str]) -> None:
    import subprocess
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore")[-2000:])


def _gen_test_video(path: str, duration: float = 5.0, size: str = "1280x720", fps: int = 30, with_audio: bool = True) -> None:
    ff = _ffmpeg_bin()
    vf = f"testsrc=size={size}:rate={fps}"
    cmd = [ff, "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", vf]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
    cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p"]
    if with_audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-ac", "2"]
    cmd += [path]
    _run(cmd)


def _gen_test_music(path: str, duration: float = 8.0) -> None:
    ff = _ffmpeg_bin()
    cmd = [ff, "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}", "-c:a", "aac", "-ar", "48000", "-ac", "2", path]
    _run(cmd)


def test_concat_then_music_overlay_smoke():
    try:
        from backend.reels_engine.render import concat_center_crop_render, add_music_overlay
    except Exception as e:
        pytest.skip(f"render import failed: {e}")

    with tempfile.TemporaryDirectory() as td:
        v1 = str(Path(td) / "v1.mp4")
        v2 = str(Path(td) / "v2.mp4")
        music = str(Path(td) / "music.m4a")
        out_dir = str(Path(td) / "out")

        _gen_test_video(v1, duration=4.0)
        _gen_test_video(v2, duration=4.0)
        _gen_test_music(music, duration=10.0)

        mp4, cover = concat_center_crop_render([v1, v2], out_dir, crossfade_sec=None, per_segment_sec=3.0)
        assert os.path.exists(mp4) and os.path.getsize(mp4) > 100_000
        final = add_music_overlay(mp4, out_dir, music_path=music, music_gain_db=-6.0, duck_music=True, music_only=True)
        # File size may vary due to container overhead; just assert it's reasonably large
        assert os.path.exists(final) and os.path.getsize(final) > 50_000


def test_single_center_crop_with_music():
    try:
        from backend.reels_engine.render import center_crop_render
    except Exception as e:
        pytest.skip(f"render import failed: {e}")

    with tempfile.TemporaryDirectory() as td:
        v1 = str(Path(td) / "v1.mp4")
        music = str(Path(td) / "music.m4a")
        out_dir = str(Path(td) / "out")

        _gen_test_video(v1, duration=6.0)
        _gen_test_music(music, duration=8.0)

        mp4, cover = center_crop_render(v1, out_dir, t0=0.0, t1=5.0, music_path=music, music_gain_db=-8.0, duck_music=True)
        assert os.path.exists(mp4) and os.path.getsize(mp4) > 100_000
        assert os.path.exists(cover)



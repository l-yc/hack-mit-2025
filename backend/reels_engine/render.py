import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

from .utils import ensure_dir


def center_crop_render(
    input_path: str,
    output_dir: str,
    t0: float,
    t1: float,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    music_path: Optional[str] = None,
    music_gain_db: float = -8.0,
    duck_music: bool = True,
) -> Tuple[str, str]:
    """
    Minimal single-clip render: trim, center-crop to 9:16, scale to 1080x1920, loudnorm.
    Returns (video_path, cover_jpg)
    """
    ensure_dir(output_dir)
    out_mp4 = str(Path(output_dir) / "reel_1080x1920.mp4")
    cover_jpg = str(Path(output_dir) / "cover.jpg")

    vf = f"scale=-2:{height},crop={width}:{height},fps={fps}"
    base_af = "loudnorm=I=-14:TP=-1.5:LRA=11, aresample=48000"

    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"
    if music_path:
        # Build filter graph to mix program audio with music and optional ducking
        afilters: List[str] = []
        # Program audio
        afilters.append("[0:a]aresample=48000, volume=1.0[a0]")
        # Music audio (loop/trim to match requested duration)
        afilters.append("[1:a]aresample=48000, volume={:.2f}dB[a1]".format(music_gain_db))
        if duck_music:
            afilters.append("[a1][a0]sidechaincompress=threshold=0.02:ratio=6:attack=5:release=300[a1d]")
            mix_inputs = "[a0][a1d]"
        else:
            mix_inputs = "[a0][a1]"
        afilters.append(f"{mix_inputs}amix=inputs=2:normalize=0:dropout_transition=0, {base_af}[am]")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss",
            f"{t0:.3f}",
            "-to",
            f"{t1:.3f}",
            "-i",
            input_path,
            "-stream_loop",
            "-1",
            "-t",
            f"{(t1 - t0):.3f}",
            "-i",
            music_path,
            "-vf",
            vf,
            "-filter_complex",
            ";".join(afilters),
            "-map",
            "0:v:0",
            "-map",
            "[am]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out_mp4,
        ]
    else:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss",
            f"{t0:.3f}",
            "-to",
            f"{t1:.3f}",
            "-i",
            input_path,
            "-vf",
            vf,
            "-af",
            base_af,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out_mp4,
        ]
    subprocess.check_call(cmd)

    # Extract cover from 1s into the clip
    cover_cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        f"{t0 + 1.0:.3f}",
        "-i",
        input_path,
        "-vframes",
        "1",
        "-vf",
        vf,
        cover_jpg,
    ]
    subprocess.check_call(cover_cmd)

    return out_mp4, cover_jpg


def concat_center_crop_render(
    inputs: List[str],
    output_dir: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crossfade_sec: Optional[float] = None,
    per_segment_sec: float = 6.0,
) -> Tuple[str, str]:
    """
    Minimal concat of multiple inputs: pre-trim not applied; center-crop/scale each, concat.
    """
    ensure_dir(output_dir)
    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"

    # Safer approach: pre-render each segment with uniform params, then concat demuxer
    seg_dir = Path(output_dir) / "segments"
    ensure_dir(seg_dir)
    seg_paths: List[str] = []
    for idx, inp in enumerate(inputs):
        seg_out = str(seg_dir / f"seg_{idx:02d}.mp4")
        vf = f"scale=-2:{height},crop={width}:{height},fps={fps}"
        af = "loudnorm=I=-14:TP=-1.5:LRA=11, aresample=48000, asetpts=PTS-STARTPTS"
        cmd_seg = [
            ffmpeg_bin,
            "-y",
            "-i",
            inp,
            "-t",
            f"{per_segment_sec:.3f}",
            "-vf",
            vf,
            "-af",
            af,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            seg_out,
        ]
        subprocess.check_call(cmd_seg)
        seg_paths.append(seg_out)

    # If crossfade requested, build filtergraph chain with xfade/acrossfade
    out_mp4 = str(Path(output_dir) / "reel_1080x1920.mp4")
    cover_jpg = str(Path(output_dir) / "cover.jpg")

    if crossfade_sec and len(seg_paths) > 1:
        args_fg = [ffmpeg_bin, "-y"]
        for p in seg_paths:
            args_fg += ["-i", p]

        filt_parts: List[str] = []
        # Prepare labeled streams with reset PTS
        for idx in range(len(seg_paths)):
            filt_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS[v{idx}]")
            filt_parts.append(f"[{idx}:a]asetpts=PTS-STARTPTS[a{idx}]")

        # Chain xfade/acrossfade
        prev_v = "v0"
        prev_a = "a0"
        cum = per_segment_sec  # current composite duration
        for idx in range(1, len(seg_paths)):
            off = max(cum - crossfade_sec, 0.0)
            out_v = f"vx{idx}"
            out_a = f"ax{idx}"
            filt_parts.append(
                f"[{prev_v}][v{idx}]xfade=transition=fade:duration={crossfade_sec:.3f}:offset={off:.3f}[{out_v}]"
            )
            filt_parts.append(
                f"[{prev_a}][a{idx}]acrossfade=d={crossfade_sec:.3f}[{out_a}]"
            )
            prev_v, prev_a = out_v, out_a
            cum = cum + per_segment_sec - crossfade_sec

        filter_complex = ";".join(filt_parts)
        cmd_fg = args_fg + [
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{prev_v}]",
            "-map",
            f"[{prev_a}]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out_mp4,
        ]
        subprocess.check_call(cmd_fg)

    else:
        # Create concat list file (ffconcat format with absolute paths)
        list_path = Path(output_dir) / "concat.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            f.write("ffconcat version 1.0\n")
            for p in seg_paths:
                f.write(f"file '{Path(p).resolve().as_posix()}'\n")

        # Concat without re-encode to keep speed (codecs/params match)
        cmd_concat = [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            out_mp4,
        ]
        try:
            subprocess.check_call(cmd_concat)
        except subprocess.CalledProcessError:
            # Fallback: re-encode on concat if stream copy fails
            cmd_concat = [
                ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                out_mp4,
            ]
            subprocess.check_call(cmd_concat)
    list_path = Path(output_dir) / "concat.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p in seg_paths:
            f.write(f"file '{Path(p).resolve().as_posix()}'\n")

    cover_jpg = str(Path(output_dir) / "cover.jpg")

    # Extract cover from first segment
    cover_cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        "1.0",
        "-i",
        seg_paths[0],
        "-vframes",
        "1",
        cover_jpg,
    ]
    subprocess.check_call(cover_cmd)

    return out_mp4, cover_jpg



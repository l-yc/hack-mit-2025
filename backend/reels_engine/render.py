import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

from .utils import ensure_dir
from .vision import Segment
from .media import probe


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run ffmpeg and raise with stderr tail on failure for better diagnostics."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr_tail = proc.stderr.decode("utf-8", errors="ignore")[-2000:]
        raise RuntimeError(f"ffmpeg failed (code {proc.returncode}):\n{stderr_tail}")


def _normalize_input(inp_path: str, out_path: str, fps: int = 30) -> str:
    """
    Re-encode input to a stable CFR H.264/AAC container to avoid filter issues.
    """
    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"

    cmd = [
        ffmpeg_bin,
        "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", inp_path,
        "-r", str(fps), "-vsync", "cfr",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        out_path,
    ]
    _run_ffmpeg(cmd)
    return out_path


def _get_rotation_degrees(path: str) -> int:
    try:
        info = probe(path) or {}
        # ffprobe json may include rotation in stream tags or side_data_list
        streams = info.get("streams") or []
        if streams:
            st0 = streams[0] or {}
            tags = st0.get("tags") or {}
            if "rotate" in tags:
                return int(str(tags.get("rotate")).strip() or 0)
            sdl = st0.get("side_data_list") or []
            if isinstance(sdl, list) and sdl:
                rot = sdl[0].get("rotation") if isinstance(sdl[0], dict) else None
                if rot is not None:
                    return int(rot)
    except Exception:
        pass
    return 0


def _rotation_prefix(path: str) -> str:
    rot = _get_rotation_degrees(path) % 360
    if rot == 90:
        return "transpose=1,"
    if rot == 270:
        return "transpose=2,"
    if rot == 180:
        return "hflip,vflip,"
    return ""


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

    # Robust 9:16 with orientation fix: apply rotation if needed, scale to height, crop/pad
    vf = (
        _rotation_prefix(input_path) +
        f"scale=-2:{height},"
        "crop=w='if(gte(iw,1080),1080,iw)':h=1920:x='if(gte(iw,1080),(iw-1080)/2,0)',"
        "pad=1080:1920:(1080-iw)/2:0,"
        f"fps={fps}"
    )
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
            "-y","-nostdin","-hide_banner","-loglevel","error",
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
            "-y","-nostdin","-hide_banner","-loglevel","error",
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
    _run_ffmpeg(cmd)

    # Extract cover from 1s into the clip
    cover_cmd = [
        ffmpeg_bin,
        "-y","-nostdin","-hide_banner","-loglevel","error",
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
    _run_ffmpeg(cover_cmd)

    return out_mp4, cover_jpg


def concat_center_crop_render(
    inputs: List[str],
    output_dir: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crossfade_sec: Optional[float] = None,
    per_segment_sec: float = 6.0,
    music_path: Optional[str] = None,
    music_gain_db: float = -8.0,
    duck_music: bool = True,
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
        # Normalize source first
        norm_inp = str(seg_dir / f"norm_{idx:02d}.mp4")
        try:
            _normalize_input(inp, norm_inp, fps=fps)
            source = norm_inp
        except Exception:
            source = inp

        seg_out = str(seg_dir / f"seg_{idx:02d}.mp4")
        vf = (
            _rotation_prefix(source) +
            f"scale=-2:{height},"
            "crop=w='if(gte(iw,1080),1080,iw)':h=1920:x='if(gte(iw,1080),(iw-1080)/2,0)',"
            "pad=1080:1920:(1080-iw)/2:0,"
            f"fps={fps}"
        )
        af = "loudnorm=I=-14:TP=-1.5:LRA=11, aresample=48000, asetpts=PTS-STARTPTS"
        cmd_seg = [
            ffmpeg_bin,
            "-y","-nostdin","-hide_banner","-loglevel","error",
            "-i",
            source,
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
        try:
            _run_ffmpeg(cmd_seg)
        except subprocess.CalledProcessError:
            # Fallback for inputs without audio: generate silent audio and map it
            cmd_seg_silent = [
                ffmpeg_bin,
                "-y","-nostdin","-hide_banner","-loglevel","error",
                "-i",
                inp,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", f"{per_segment_sec:.3f}",
                "-shortest",
                "-filter_complex", f"[0:v]{vf}[v]",
                "-map", "[v]",
                "-map", "1:a:0",
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
            _run_ffmpeg(cmd_seg_silent)
        seg_paths.append(seg_out)

    # If crossfade requested, build filtergraph chain with xfade/acrossfade
    out_mp4 = str(Path(output_dir) / "reel_1080x1920.mp4")
    cover_jpg = str(Path(output_dir) / "cover.jpg")

    if (crossfade_sec and len(seg_paths) > 1) or music_path:
        args_fg = [ffmpeg_bin, "-y"]
        for p in seg_paths:
            args_fg += ["-i", p]

        filt_parts: List[str] = []
        # Prepare labeled streams with consistent fps/format and reset PTS
        for idx in range(len(seg_paths)):
            filt_parts.append(
                f"[{idx}:v]fps={fps},format=yuv420p,setpts=PTS-STARTPTS[v{idx}]"
            )
            filt_parts.append(
                f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{idx}]"
            )

        # Build program A/V either via xfade chain or concat filter
        if crossfade_sec and len(seg_paths) > 1:
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
            v_final = prev_v
            a_prog = prev_a
        else:
            # Concat N segments to [vc][ac]
            maps = "".join([f"[v{i}][a{i}]" for i in range(len(seg_paths))])
            filt_parts.append(
                maps + f"concat=n={len(seg_paths)}:v=1:a=1[vc][ac]"
            )
            v_final = "vc"
            a_prog = "ac"

        # Optional background music mixing
        if music_path:
            total_len = len(seg_paths) * per_segment_sec - max(len(seg_paths) - 1, 0) * (crossfade_sec or 0.0)
            args_fg += ["-stream_loop", "-1", "-t", f"{total_len:.3f}", "-i", music_path]
            music_idx = len(seg_paths)
            filt_parts.append(f"[{music_idx}:a]aresample=48000, volume={music_gain_db:.2f}dB[amusic]")
            if duck_music:
                filt_parts.append(f"[amusic][{a_prog}]sidechaincompress=threshold=0.02:ratio=6:attack=5:release=300[amusicd]")
                mix_in = f"[{a_prog}][amusicd]"
            else:
                mix_in = f"[{a_prog}][amusic]"
            filt_parts.append(mix_in + "amix=inputs=2:normalize=0:dropout_transition=0, aresample=48000[am]")
            a_out = "am"
        else:
            a_out = a_prog

        filter_complex = ";".join(filt_parts)
        cmd_fg = args_fg + [
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{v_final}]",
            "-map",
            f"[{a_out}]",
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
        _run_ffmpeg(cmd_fg)

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
            _run_ffmpeg(cmd_concat)
        except subprocess.CalledProcessError:
            # Fallback: re-encode on concat if stream copy fails
            cmd_concat = [
                ffmpeg_bin,
                "-y","-nostdin","-hide_banner","-loglevel","error",
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
            _run_ffmpeg(cmd_concat)
    list_path = Path(output_dir) / "concat.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p in seg_paths:
            f.write(f"file '{Path(p).resolve().as_posix()}'\n")

    cover_jpg = str(Path(output_dir) / "cover.jpg")

    # Extract cover from first segment
    cover_cmd = [
        ffmpeg_bin,
        "-y","-nostdin","-hide_banner","-loglevel","error",
        "-ss",
        "1.0",
        "-i",
        seg_paths[0],
        "-vframes",
        "1",
        cover_jpg,
    ]
    _run_ffmpeg(cover_cmd)

    return out_mp4, cover_jpg


def add_music_overlay(
    input_video_path: str,
    output_dir: str,
    music_path: str,
    music_gain_db: float = -8.0,
    duck_music: bool = True,
    music_only: bool = False,
) -> str:
    """
    Mix background music into an existing video file's audio, with optional ducking.
    Returns new video path.
    """
    ensure_dir(output_dir)
    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"

    # Ensure we don't write to the same file as the input
    default_out = Path(output_dir) / "reel_1080x1920.mp4"
    try:
        same = Path(input_video_path).resolve() == default_out.resolve()
    except Exception:
        same = False
    out_target = default_out.with_name(default_out.stem + "_music" + default_out.suffix) if same else default_out
    out_mp4 = str(out_target)

    afilters: List[str] = []
    if music_only:
        afilters.append(f"[1:a]aresample=48000,volume={music_gain_db:.2f}dB[am]")
        amap = "[am]"
    else:
        # Program + music mix with optional ducking
        afilters.append("[0:a]aresample=48000,volume=1.0[a0]")
        afilters.append(f"[1:a]aresample=48000,volume={music_gain_db:.2f}dB[a1]")
        if duck_music:
            afilters.append("[a1][a0]sidechaincompress=threshold=0.02:ratio=6:attack=5:release=300[a1d]")
            mix_inputs = "[a0][a1d]"
        else:
            mix_inputs = "[a0][a1]"
        afilters.append(mix_inputs + "amix=inputs=2:normalize=0:dropout_transition=0,aresample=48000[am]")
        amap = "[am]"

    cmd = [
        ffmpeg_bin,
        "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", input_video_path,
        "-stream_loop", "-1",
        "-i", music_path,
        "-filter_complex", ";".join(afilters),
        "-map", "0:v:0",
        "-map", amap,
        "-c:v", "copy",
        "-shortest",
        "-c:a", "aac", "-b:a", "192k",
        out_mp4,
    ]
    _run_ffmpeg(cmd)
    return out_mp4


def concat_segments_render(
    segments: List[Segment],
    output_dir: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Tuple[str, str]:
    """
    Trim arbitrary [t0,t1] from possibly different sources, center-crop to 9:16, then concat.
    """
    ensure_dir(output_dir)
    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"

    seg_dir = Path(output_dir) / "segments"
    ensure_dir(seg_dir)
    seg_paths: List[str] = []

    vf = (
        f"scale=-2:{height},"
        "crop=w='if(gte(iw,1080),1080,iw)':h=1920:x='if(gte(iw,1080),(iw-1080)/2,0)',"
        "pad=1080:1920:(1080-iw)/2:0,"
        f"fps={fps}"
    )
    for idx, seg in enumerate(segments):
        out = str(seg_dir / f"seg_{idx:02d}.mp4")
        rot_prefix = _rotation_prefix(seg.path)
        vf_seg = rot_prefix + vf
        # Add a short fade-out on the last segment for smoother ending
        if idx == len(segments) - 1:
            dur = max(0.5, seg.t1 - seg.t0)
            fade_d = min(0.7, dur / 2)
            vf_seg = vf_seg + f",fade=t=out:st={max(dur - fade_d, 0):.3f}:d={fade_d:.3f}"
        cmd = [
            ffmpeg_bin,
            "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{seg.t0:.3f}",
            "-to", f"{seg.t1:.3f}",
            "-i", seg.path,
            "-vf", vf_seg,
            "-af", "aresample=48000",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            out,
        ]
        _run_ffmpeg(cmd)
        seg_paths.append(out)

    # concat list
    list_path = Path(output_dir) / "concat.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p in seg_paths:
            f.write(f"file '{Path(p).resolve().as_posix()}'\n")

    out_mp4 = str(Path(output_dir) / "reel_1080x1920.mp4")
    cover_jpg = str(Path(output_dir) / "cover.jpg")
    cmd_concat = [
        ffmpeg_bin,
        "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        out_mp4,
    ]
    try:
        _run_ffmpeg(cmd_concat)
    except Exception:
        cmd_concat = [
            ffmpeg_bin,
            "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_path),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            out_mp4,
        ]
        _run_ffmpeg(cmd_concat)

    # cover from first segment
    cover_cmd = [
        ffmpeg_bin, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", "0.5", "-i", seg_paths[0], "-vframes", "1", cover_jpg,
    ]
    _run_ffmpeg(cover_cmd)
    return out_mp4, cover_jpg



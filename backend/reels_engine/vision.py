from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .utils import ensure_dir


def _ffmpeg_bin() -> str:
    exe = os.environ.get("FFMPEG_BIN")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@dataclass
class Segment:
    path: str
    t0: float
    t1: float
    score: float


def score_motion_segments(
    input_path: str,
    per_segment_sec: float = 3.0,
    target_fps: int = 10,
    max_segments: int = 5,
) -> List[Segment]:
    """
    Fast motion scoring using ffmpeg filters (no python decode):
    - downscale
    - fps target_fps
    - tblend difference between consecutive frames
    - crop/scale not required here; just aggregate absolute differences
    """
    ff = _ffmpeg_bin()
    # Compute a simple motion metric using ffmpeg and read framewise power from stderr
    # We will approximate by decoding frames and calculating frame difference energy via psnr/diff filter.
    # Simpler: use -vf "fps=10,format=gray,signalstats" and parse YDIF.
    cmd = [
        ff,
        "-hide_banner",
        "-loglevel",
        "info",
        "-i",
        input_path,
        "-vf",
        f"fps={target_fps},format=gray,signalstats",
        "-f",
        "null",
        "-",
    ]
    proc = _run(cmd)
    text = (proc.stderr or proc.stdout).decode("utf-8", errors="ignore")

    # Parse lines containing "Parsed_signalstats" and extract YDIF (difference luma metric)
    import re

    diffs: List[float] = []
    for line in text.splitlines():
        # e.g., ... signalstats: YDIF:0.0123 ...
        m = re.search(r"YDIF:([0-9.]+)", line)
        if m:
            try:
                diffs.append(float(m.group(1)))
            except Exception:
                pass

    if not diffs:
        return []

    # Build windowed means over per_segment_sec
    hop = 1.0 / target_fps
    win = max(int(round(per_segment_sec / hop)), 1)
    scores: List[Tuple[int, float]] = []
    import math
    for i in range(0, max(0, len(diffs) - win + 1)):
        s = sum(diffs[i : i + win]) / win
        scores.append((i, s))

    # Pick top segments, non-overlapping
    scores.sort(key=lambda x: x[1], reverse=True)
    chosen: List[Tuple[int, float]] = []
    last_end = -10**9
    for idx, sc in scores:
        t0 = idx * hop
        t1 = t0 + per_segment_sec
        if t0 >= last_end:
            chosen.append((idx, sc))
            last_end = t1
        if len(chosen) >= max_segments:
            break

    return [Segment(path=input_path, t0=i * hop, t1=i * hop + per_segment_sec, score=sc) for i, sc in chosen]



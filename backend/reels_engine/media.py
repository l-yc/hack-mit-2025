import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, List

from .utils import ensure_dir


def probe(path: str) -> Dict[str, Any]:
    """
    Use ffprobe to read basic metadata. If ffprobe is unavailable, return an empty dict.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,avg_frame_rate,rotation",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        import json as _json
        return _json.loads(out.decode("utf-8"))
    except Exception:
        # Graceful fallback for environments without ffprobe
        return {}


def download(url: str, tmp_dir: str) -> str:
    """
    Minimal downloader: supports local paths and http(s). S3/GCS TBD.
    """
    ensure_dir(tmp_dir)
    if url.startswith("http://") or url.startswith("https://"):
        import requests

        local = Path(tmp_dir) / f"in_{uuid.uuid4().hex}.mp4"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return str(local)
    if url.startswith("s3://") or url.startswith("gs://"):
        # Placeholder: assume pre-mounted or local mirror path
        return url
    # Assume local path
    if os.path.exists(url):
        local = Path(tmp_dir) / f"in_{uuid.uuid4().hex}{Path(url).suffix or '.mp4'}"
        shutil.copy(url, local)
        return str(local)
    raise FileNotFoundError(url)


def download_many(urls: List[str], tmp_dir: str) -> List[str]:
    return [download(u, tmp_dir) for u in urls]



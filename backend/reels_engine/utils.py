import hashlib
import json
import os
from pathlib import Path
from typing import Tuple


def ensure_dir(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def hash_video_like(path: str) -> str:
    """
    Approximate video hash using first 1MB bytes and filename to allow caching.
    """
    h = hashlib.sha1()
    p = Path(path)
    h.update(p.name.encode())
    try:
        with open(path, "rb") as f:
            h.update(f.read(1024 * 1024))
    except Exception:
        pass
    return h.hexdigest()[:16]


def write_json(path: str | Path, obj) -> str:
    path = str(path)
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    return path



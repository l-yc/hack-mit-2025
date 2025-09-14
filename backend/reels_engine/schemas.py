from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time


@dataclass
class Postpass:
    nano_banana: bool = False
    tone: Optional[str] = None


@dataclass
class JobRequest:
    video_url: Optional[str] = None
    video_urls: List[str] = field(default_factory=list)
    directory: Optional[str] = None
    max_files: int = 12
    per_segment_sec: float = 3.0
    music_url: Optional[str] = None
    music_gain_db: float = -8.0
    duck_music: bool = True
    music_only: bool = False
    end_with_low: bool = True
    mode: str = "single"
    target_duration_sec: float = 15.0
    min_duration_sec: float = 9.0
    max_duration_sec: float = 20.0
    aspect: str = "9:16"
    speech_mode: bool = True
    music_mode: bool = False
    top_k_candidates: int = 3
    keywords: List[str] = field(default_factory=list)
    brand_faces_whitelist: List[str] = field(default_factory=list)
    crop_safe_margin_pct: float = 0.05
    postpass: Postpass = field(default_factory=Postpass)
    webhook_url: Optional[str] = None


@dataclass
class ArtifactPaths:
    best_reel_mp4: Optional[str] = None
    alt_candidates: List[Dict[str, Any]] = field(default_factory=list)
    captions_srt: Optional[str] = None
    timeline_json: Optional[str] = None
    cover_jpg: Optional[str] = None


@dataclass
class Job:
    id: str
    request: JobRequest
    status: str = "queued"
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    error: Optional[str] = None
    artifacts: ArtifactPaths = field(default_factory=ArtifactPaths)



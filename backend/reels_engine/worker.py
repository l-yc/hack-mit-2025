import os
import queue
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from .media import download, download_many, probe
from .render import center_crop_render, concat_center_crop_render
from .schemas import Job, JobRequest, ArtifactPaths
from .utils import ensure_dir, write_json


class JobManager:
    def __init__(self, uploads_root: str):
        self.uploads_root = uploads_root
        self.jobs: Dict[str, Job] = {}
        self.q: "queue.Queue[str]" = queue.Queue()
        self.thread: Optional[threading.Thread] = None
        ensure_dir(self.uploads_root)

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def enqueue(self, req: JobRequest) -> Job:
        job_id = f"r_{uuid.uuid4().hex[:10]}"
        job = Job(id=job_id, request=req)
        self.jobs[job_id] = job
        self.q.put(job_id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def _run(self) -> None:
        while True:
            try:
                job_id = self.q.get()
                job = self.jobs.get(job_id)
                if not job:
                    continue
                self._process(job)
            except Exception:
                time.sleep(0.1)

    def _process(self, job: Job) -> None:
        job.status = "processing"
        job.updated_at = time.time()
        out_dir = Path(self.uploads_root) / "reels" / job.id
        ensure_dir(out_dir)

        try:
            # Download input(s)
            tmp_dir = str(Path(self.uploads_root) / "tmp" / job.id)
            ensure_dir(tmp_dir)
            inputs: list[str]
            if job.request.video_urls:
                inputs = download_many(job.request.video_urls, tmp_dir)
            elif job.request.video_url:
                inputs = [download(job.request.video_url, tmp_dir)]
            else:
                raise ValueError("No video_url(s) provided")

            # Minimal selection: single vs montage concat
            if job.request.mode == "montage" and len(inputs) > 1:
                mp4_path, cover_path = concat_center_crop_render(
                    inputs=inputs,
                    output_dir=str(out_dir),
                    crossfade_sec=0.25,
                )
                t0, t1 = 0.0, 0.0
            else:
                local_path = inputs[0]
                _ = probe(local_path)
                t0 = 0.0
                t1 = max(job.request.target_duration_sec, 3.0)
                mp4_path, cover_path = center_crop_render(
                    input_path=local_path,
                    output_dir=str(out_dir),
                    t0=t0,
                    t1=t1,
                    music_path=job.request.music_url,
                    music_gain_db=job.request.music_gain_db,
                    duck_music=job.request.duck_music,
                )

            artifacts = ArtifactPaths(
                best_reel_mp4=str(Path("/photos") / Path(mp4_path).relative_to(self.uploads_root)).replace("\\", "/"),
                alt_candidates=[{"start": t0, "end": t1, "score": 0.0}],
                captions_srt=None,
                timeline_json=str(Path("/photos") / Path(write_json(Path(out_dir)/"timeline.json", {"t0": t0, "t1": t1})).relative_to(self.uploads_root)).replace("\\", "/"),
                cover_jpg=str(Path("/photos") / Path(cover_path).relative_to(self.uploads_root)).replace("\\", "/"),
            )

            job.artifacts = artifacts
            job.status = "completed"
            job.updated_at = time.time()

            write_json(Path(out_dir)/"job.json", {"job": asdict(job)})
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.updated_at = time.time()
            write_json(Path(out_dir)/"job.json", {"job": asdict(job)})


job_manager = JobManager(uploads_root=os.environ.get("UPLOADS_ROOT", "uploads"))



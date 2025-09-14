"""
Minimal reels processing engine: in-memory job queue with a simple
ffmpeg-based single-clip render. Designed to be extended with full
feature extraction, scoring, and selection.
"""

from .worker import job_manager

__all__ = ["job_manager"]



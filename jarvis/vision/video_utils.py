"""
Video frame extraction utilities for JARVIS.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """
    Extract frames from video files using OpenCV.
    """

    @staticmethod
    def extract_frames(video_path: str, max_frames: int = 5) -> list[str]:
        """
        Extract frames at evenly spaced intervals from a video.

        Args:
            video_path: Path to the video file
            max_frames: Maximum number of frames to extract

        Returns:
            List of paths to extracted frame images, or empty list if unavailable
        """
        try:
            import cv2
        except ImportError:
            logger.debug("OpenCV not available for frame extraction")
            return []

        video_file = Path(video_path)
        if not video_file.exists():
            return []

        cap = cv2.VideoCapture(str(video_file))
        if not cap.isOpened():
            return []

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            cap.release()
            return []

        step = max(1, frame_count // max_frames)
        tmpdir = tempfile.mkdtemp(prefix="jarvis_frames_")
        frame_paths: list[str] = []

        for idx in range(0, frame_count, step):
            if len(frame_paths) >= max_frames:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            out_path = Path(tmpdir) / f"frame_{idx:06d}.png"
            cv2.imwrite(str(out_path), frame)
            frame_paths.append(str(out_path))

        cap.release()
        return frame_paths

"""
Vision module for JARVIS.
Provides screen capture, camera capture, and visual analysis.
"""

from jarvis.vision.camera import CameraCapture
from jarvis.vision.screen import ScreenAnalyzer, ScreenCapture, ScreenRegion, VisionCapture

__all__ = [
    "CameraCapture",
    "ScreenAnalyzer",
    "ScreenCapture",
    "ScreenRegion",
    "VisionCapture",
]

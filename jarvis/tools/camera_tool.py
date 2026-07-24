"""
JARVIS Camera Tool
==================
Registers camera/vision capability in the ToolRegistry by wrapping the
EXISTING jarvis.vision.camera.CameraCapture and jarvis.vision.screen.ScreenCapture.

Design rules:
- NEVER duplicate CameraCapture / OpenCV logic
- ONLY delegate to existing vision implementations
- Gracefully handle missing opencv/cv2 dependency
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from jarvis.tools.base import PermissionLevel, ReadOnlyTool, ToolResult

logger = logging.getLogger(__name__)

_CAPTURE_DIR = Path.home() / ".jarvis" / "captures"


def _get_capture_dir() -> Path:
    _CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    return _CAPTURE_DIR


class CameraTool(ReadOnlyTool):
    """
    Captures images from the camera or screen using existing JARVIS vision modules.

    Delegating order:
      1. jarvis.vision.camera.CameraCapture — physical webcam (OpenCV)
      2. jarvis.vision.screen.ScreenCapture — desktop screenshot (mss)
    """

    name: str = "open_camera"
    description: str = (
        "Open the camera and capture an image, or take a screenshot. "
        "Use for: open camera, take photo, capture image, take screenshot, "
        "see what I look like, scan environment, visual inspection."
    )
    permission_level = PermissionLevel.ASK_ONCE

    KEYWORDS = [
        "camera", "capture", "photo", "picture", "screenshot", "snap",
        "webcam", "look", "see", "visual", "image", "screen", "display",
    ]

    @property
    def category(self) -> str:
        return "media"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["camera", "screen", "auto"],
                    "description": (
                        "Capture source: 'camera' for webcam, "
                        "'screen' for desktop screenshot, 'auto' tries camera first"
                    ),
                    "default": "auto",
                },
                "device_index": {
                    "type": "integer",
                    "description": "Camera device index (default 0)",
                    "default": 0,
                },
                "analyze": {
                    "type": "boolean",
                    "description": "Whether to analyze the captured image with AI vision",
                    "default": False,
                },
            },
            "required": [],
        }

    def __init__(self) -> None:
        super().__init__()

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        source = input_data.get("source", "auto")
        device_index = int(input_data.get("device_index", 0))
        analyze = bool(input_data.get("analyze", False))

        logger.info("[Executor] CameraTool: source=%s", source)

        img_bytes: bytes | None = None
        img_source_used = ""

        # ── Try camera ──────────────────────────────────────────────────
        if source in ("camera", "auto"):
            img_bytes, img_source_used = await self._try_camera(device_index)

        # ── Fall back to screen capture ──────────────────────────────────
        if img_bytes is None and source in ("screen", "auto"):
            img_bytes, img_source_used = await self._try_screen()

        if img_bytes is None:
            return ToolResult(
                success=False,
                output=None,
                error=(
                    "Camera and screen capture both unavailable.\n"
                    "To enable camera: install opencv-python (`pip install opencv-python`)\n"
                    "To enable screen capture: install mss (`pip install mss`)"
                ),
            )

        # ── Save to disk ─────────────────────────────────────────────────
        ts = int(time.time())
        out_path = _get_capture_dir() / f"capture_{ts}.jpg"
        out_path.write_bytes(img_bytes)

        output: dict[str, Any] = {
            "image_path": str(out_path),
            "source": img_source_used,
            "size_bytes": len(img_bytes),
            "message": f"Captured image via {img_source_used}: {out_path}",
        }

        # ── Optional AI analysis ──────────────────────────────────────────
        if analyze:
            analysis = await self._analyze_image(str(out_path))
            output["analysis"] = analysis

        logger.info("[Success] CameraTool: saved %s (%d bytes)", out_path, len(img_bytes))
        return ToolResult(success=True, output=output)

    async def _try_camera(self, device_index: int) -> tuple[bytes | None, str]:
        """Use existing CameraCapture from jarvis.vision.camera."""
        try:
            import asyncio

            from jarvis.vision.camera import CameraCapture

            cam = CameraCapture(device_index=device_index)
            # CameraCapture.capture() is synchronous — run in thread with timeout
            img_bytes = await asyncio.wait_for(
                asyncio.to_thread(cam.capture), timeout=3.0
            )
            cam.release()
            return img_bytes, f"webcam[{device_index}]"
        except (TimeoutError, RuntimeError, Exception) as e:
            logger.debug("[CameraTool] Camera unavailable: %s", e)
            return None, ""

    async def _try_screen(self) -> tuple[bytes | None, str]:
        """Use existing ScreenCapture from jarvis.vision.screen."""
        try:
            import asyncio

            from jarvis.vision.screen import ScreenCapture

            sc = ScreenCapture()
            img_bytes = await asyncio.wait_for(
                asyncio.to_thread(sc.capture), timeout=3.0
            )
            return img_bytes, "screen"
        except (TimeoutError, Exception) as e:
            logger.debug("[CameraTool] Screen capture error: %s", e)

        # Fallback: try desktop automation screenshot
        try:
            import asyncio

            from jarvis.desktop.automation import get_desktop_automation

            automation = get_desktop_automation()
            path = await asyncio.wait_for(automation.take_screenshot(), timeout=3.0)
            if path:
                from pathlib import Path as _Path
                img_bytes = _Path(path).read_bytes()
                return img_bytes, "desktop_screenshot"
        except Exception as e:
            logger.debug("[CameraTool] Desktop automation screenshot error: %s", e)

        return None, ""


    async def _analyze_image(self, image_path: str) -> str:
        """Delegate to existing VisionAgent for AI analysis."""
        try:
            from jarvis.agents.vision_agent import VisionAgent
            agent = VisionAgent()
            result = await agent.understand_image(image_path)
            return result.description or "No description available"
        except Exception as e:
            logger.debug("[CameraTool] Vision analysis failed: %s", e)
            return f"Image saved but analysis unavailable: {e}"


class ScreenshotTool(ReadOnlyTool):
    """
    Dedicated screenshot tool — wraps existing ScreenCapture.

    Registered separately so the planner can choose between
    'camera' (webcam) and 'screenshot' (desktop).
    """

    name: str = "take_screenshot"
    description: str = (
        "Take a screenshot of the current desktop or a specific monitor. "
        "Use for: screenshot, screen capture, capture screen, show screen."
    )
    permission_level = PermissionLevel.AUTOMATIC

    KEYWORDS = ["screenshot", "screen", "capture", "desktop", "monitor", "display"]

    @property
    def category(self) -> str:
        return "media"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "monitor": {
                    "type": "integer",
                    "description": "Monitor index (0 = all monitors, 1+ = specific)",
                    "default": 0,
                },
                "analyze": {
                    "type": "boolean",
                    "description": "Analyze the screenshot with AI",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        analyze = bool(input_data.get("analyze", False))
        logger.info("[Executor] ScreenshotTool")

        try:
            # Try desktop automation first (most reliable)
            from jarvis.desktop.automation import get_desktop_automation
            automation = get_desktop_automation()
            path = await automation.take_screenshot()
            if path:
                output: dict[str, Any] = {
                    "image_path": path,
                    "message": f"Screenshot saved: {path}",
                }
                if analyze:
                    try:
                        from jarvis.agents.vision_agent import VisionAgent
                        agent = VisionAgent()
                        result = await agent.understand_image(path)
                        output["analysis"] = result.description
                    except Exception:
                        pass
                logger.info("[Success] Screenshot: %s", path)
                return ToolResult(success=True, output=output)
        except Exception as e:
            logger.debug("[ScreenshotTool] Automation failed: %s", e)

        # Fallback: ScreenCapture
        try:
            import asyncio

            from jarvis.vision.screen import ScreenCapture

            sc = ScreenCapture()
            img_bytes = await asyncio.to_thread(sc.capture)
            ts = int(time.time())
            out_path = _get_capture_dir() / f"screenshot_{ts}.png"
            out_path.write_bytes(img_bytes)
            logger.info("[Success] Screenshot via ScreenCapture: %s", out_path)
            return ToolResult(
                success=True,
                output={"image_path": str(out_path), "message": f"Screenshot: {out_path}"},
            )
        except Exception as e:
            logger.error("[Failure] Screenshot failed: %s", e)
            return ToolResult(success=False, output=None, error=f"Screenshot failed: {e}")

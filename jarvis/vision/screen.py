"""
Screen capture for JARVIS - Enhanced vision module.
Provides full-screen capture, region capture, and AI analysis.
"""

import io
import base64
from typing import Optional, Tuple, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ScreenRegion:
    """Represents a screen region to capture."""
    x: int
    y: int
    width: int
    height: int


class ScreenCapture:
    """
    Enhanced screen capture using mss library.
    Supports full screen, regions, and multiple monitors.
    """

    def __init__(self, monitor: int = 1):
        self._mss = None
        self._monitor = monitor
        self._initialize()

    def _initialize(self):
        """Initialize mss."""
        try:
            import mss
            self._mss = mss.MSS()
        except ImportError:
            print("[Vision] mss not available")

    def capture(self, output_path: Optional[Path] = None) -> bytes:
        """
        Capture the full screen.

        Args:
            output_path: Optional path to save the screenshot

        Returns:
            Screenshot as PNG bytes
        """
        if self._mss is None:
            raise RuntimeError("Screen capture not available (mss not installed)")

        try:
            shot = self._mss.grab(self._mss.monitors[self._monitor])

            if output_path:
                mss.tools.to_png(shot.rgb, shot.size, output=str(output_path))

            return mss.tools.to_png(shot.rgb, shot.size)

        except Exception as e:
            raise RuntimeError(f"Screen capture failed: {e}")

    def capture_region(self, region: ScreenRegion, output_path: Optional[Path] = None) -> bytes:
        """
        Capture a specific screen region.

        Args:
            region: ScreenRegion to capture
            output_path: Optional path to save the screenshot

        Returns:
            Screenshot as PNG bytes
        """
        if self._mss is None:
            raise RuntimeError("Screen capture not available")

        try:
            import mss
            monitor = {
                "left": region.x,
                "top": region.y,
                "width": region.width,
                "height": region.height
            }
            shot = self._mss.grab(monitor)

            if output_path:
                mss.tools.to_png(shot.rgb, shot.size, output=str(output_path))

            return mss.tools.to_png(shot.rgb, shot.size)

        except Exception as e:
            raise RuntimeError(f"Region capture failed: {e}")

    def capture_to_jpeg(self, quality: int = 85) -> bytes:
        """Capture screen and return as JPEG."""
        png_data = self.capture()

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(png_data))
            img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()

        except ImportError:
            return png_data

    def capture_to_base64(self, format: str = "png") -> str:
        """
        Capture screen and return as base64 string.

        Args:
            format: Image format ('png' or 'jpeg')

        Returns:
            Base64 encoded image string
        """
        if format.lower() == "jpeg":
            data = self.capture_to_jpeg()
        else:
            data = self.capture()

        return base64.b64encode(data).decode("utf-8")

    def get_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        if self._mss is None:
            return (0, 0)

        try:
            monitor = self._mss.monitors[self._monitor]
            return (monitor["width"], monitor["height"])
        except Exception:
            return (0, 0)

    def get_all_monitors(self) -> List[dict]:
        """Get information about all monitors."""
        if self._mss is None:
            return []

        try:
            return [
                {"index": i, **m}
                for i, m in enumerate(self._mss.monitors)
            ]
        except Exception:
            return []

    def save_screenshot(self, path: Path, format: str = "png") -> Path:
        """
        Save screenshot to file.

        Args:
            path: Output file path
            format: Image format ('png' or 'jpeg')

        Returns:
            Path to saved file
        """
        if format.lower() == "jpeg":
            data = self.capture_to_jpeg()
        else:
            data = self.capture()

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

        return path


class ScreenAnalyzer:
    """
    Analyzes screenshots to detect UI elements, text, and objects.
    """

    def __init__(self):
        self._ocr_available = False
        self._cv2_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """Check available dependencies."""
        try:
            import cv2
            self._cv2_available = True
        except ImportError:
            print("[Vision] OpenCV not available")

        try:
            import pytesseract
            self._ocr_available = True
        except ImportError:
            print("[Vision] pytesseract not available for OCR")

    def extract_text(self, image_data: bytes) -> str:
        """
        Extract text from screenshot using OCR.

        Args:
            image_data: PNG image bytes

        Returns:
            Extracted text
        """
        if not self._ocr_available:
            return "OCR not available (pytesseract not installed)"

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(img)
            return text.strip()

        except Exception as e:
            return f"OCR failed: {e}"

    def detect_buttons(self, image_data: bytes) -> List[dict]:
        """
        Detect button-like elements in screenshot.

        Args:
            image_data: PNG image bytes

        Returns:
            List of detected button regions
        """
        if not self._cv2_available:
            return []

        try:
            import cv2
            import numpy as np
            from PIL import Image

            # Convert to OpenCV format
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply threshold to detect bright rectangular regions
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

            # Find contours
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            buttons = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if 20 < w < 300 and 10 < h < 100:  # Typical button size
                    buttons.append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                        "center": (int(x + w/2), int(y + h/2))
                    })

            return buttons

        except Exception:
            return []

    def get_color_at_point(self, image_data: bytes, x: int, y: int) -> Tuple[int, int, int]:
        """
        Get the color of a specific pixel.

        Args:
            image_data: PNG image bytes
            x: X coordinate
            y: Y coordinate

        Returns:
            RGB tuple (r, g, b)
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))
            if img.mode != "RGB":
                img = img.convert("RGB")

            return img.getpixel((x, y))

        except Exception:
            return (0, 0, 0)

    def compare_screenshots(self, img1: bytes, img2: bytes) -> float:
        """
        Compare two screenshots and return similarity (0.0 - 1.0).

        Args:
            img1: First image bytes
            img2: Second image bytes

        Returns:
            Similarity score
        """
        if not self._cv2_available:
            return 0.0

        try:
            import cv2
            import numpy as np

            # Decode images
            nparr1 = np.frombuffer(img1, np.uint8)
            nparr2 = np.frombuffer(img2, np.uint8)

            img1_cv = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
            img2_cv = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)

            if img1_cv is None or img2_cv is None:
                return 0.0

            # Resize to same dimensions
            h, w = img1_cv.shape[:2]
            img2_cv = cv2.resize(img2_cv, (w, h))

            # Calculate difference
            diff = cv2.absdiff(img1_cv, img2_cv)
            diff_sum = np.sum(diff)
            max_diff = w * h * 255 * 3

            return 1.0 - (diff_sum / max_diff)

        except Exception:
            return 0.0


class VisionCapture:
    """
    Combined screen and camera capture for JARVIS.
    """

    def __init__(self):
        self.screen = ScreenCapture()
        self.screen_analyzer = ScreenAnalyzer()
        self._camera = None

    async def capture_screen(self, path: Optional[Path] = None) -> bytes:
        """Capture screen."""
        return self.screen.capture(path)

    async def capture_region(self, region: ScreenRegion) -> bytes:
        """Capture screen region."""
        return self.screen.capture_region(region)

    async def analyze_screen(self) -> dict:
        """
        Capture screen and analyze its contents.

        Returns:
            Dictionary with screenshot data and analysis
        """
        image_data = self.screen.capture()

        analysis = {
            "image": image_data,
            "base64": self.screen.capture_to_base64(),
            "dimensions": self.screen.get_dimensions(),
        }

        # Add OCR if available
        text = self.screen_analyzer.extract_text(image_data)
        if text and "not available" not in text:
            analysis["text"] = text

        # Add button detection
        buttons = self.screen_analyzer.detect_buttons(image_data)
        if buttons:
            analysis["buttons"] = buttons

        return analysis

    def init_camera(self):
        """Initialize camera capture."""
        if self._camera is None:
            from jarvis.vision.camera import CameraCapture
            self._camera = CameraCapture()

    async def capture_camera(self) -> Optional[bytes]:
        """Capture from camera."""
        if self._camera is None:
            self.init_camera()
        return await self._camera.capture_frame()

"""
Camera capture for JARVIS.
Adapted from Mark-XXXIX-OR's screen_processor.py
"""

from typing import List


class CameraCapture:
    """
    Camera capture using OpenCV.
    """

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._capture = None

    def _initialize(self):
        """Initialize the camera."""
        try:
            import cv2
            self._capture = cv2.VideoCapture(self.device_index)
            if not self._capture.isOpened():
                raise RuntimeError(f"Camera {self.device_index} not available")
        except ImportError:
            raise RuntimeError("Camera capture not available (opencv not installed)")

    def capture(self) -> bytes:
        """
        Capture a single frame from the camera.

        Returns:
            Frame as JPEG bytes
        """
        if self._capture is None:
            self._initialize()

        try:
            import cv2

            ret, frame = self._capture.read()
            if not ret:
                raise RuntimeError("Failed to capture frame")

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to JPEG
            from PIL import Image
            import io

            img = Image.fromarray(rgb_frame)
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return buf.getvalue()

        except ImportError:
            raise RuntimeError("PIL not available for image encoding")
        except Exception as e:
            raise RuntimeError(f"Camera capture failed: {e}")

    def list_devices(self) -> List[dict]:
        """
        List available camera devices.

        Returns:
            List of device info dicts
        """
        devices = []

        try:
            import cv2

            # Try to open cameras 0-5
            for i in range(6):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    devices.append({
                        "index": i,
                        "available": True,
                        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    })
                    cap.release()

        except ImportError:
            pass

        return devices

    def release(self):
        """Release the camera."""
        if self._capture:
            try:
                self._capture.release()
            except Exception:
                pass
            self._capture = None

    def __del__(self):
        """Cleanup on deletion."""
        self.release()

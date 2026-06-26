"""
JARVIS Vision Module
Screenshot analysis, OCR, object detection, and GUI understanding.
"""

import asyncio
import base64
import io
import logging
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("jarvis.vision")


@dataclass
class VisionConfig:
    """Vision system configuration."""
    # OCR settings
    ocr_language: str = "eng"
    ocr_confidence_threshold: float = 0.5
    
    # Model settings
    use_gpu: bool = False
    model_size: str = "medium"  # small, medium, large
    
    # Screenshot settings
    screenshot_format: str = "png"
    screenshot_quality: int = 90


@dataclass
class ScreenRegion:
    """A region of the screen."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class DetectedElement:
    """A detected UI element."""
    label: str
    confidence: float
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    text: Optional[str] = None
    element_type: Optional[str] = None


class ScreenCapture:
    """
    Screen capture functionality.
    
    Supports cross-platform screenshots.
    """
    
    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._platform = platform.system().lower()
    
    async def capture_screen(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> bytes:
        """
        Capture screenshot.
        
        Args:
            region: Optional region to capture (None = full screen)
            
        Returns:
            Screenshot as bytes
        """
        if self._platform == "windows":
            return await self._capture_windows(region)
        elif self._platform == "darwin":
            return await self._capture_macos(region)
        else:
            return await self._capture_linux(region)
    
    async def _capture_windows(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> bytes:
        """Capture screenshot on Windows."""
        try:
            import pyautogui
            
            if region:
                screenshot = pyautogui.screenshot(region=region.bounds)
            else:
                screenshot = pyautogui.screenshot()
            
            # Convert to bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format=self.config.screenshot_format)
            return buffer.getvalue()
            
        except ImportError:
            logger.warning("pyautogui not available")
            # Fallback to PIL
            return await self._capture_pil(region)
    
    async def _capture_macos(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> bytes:
        """Capture screenshot on macOS."""
        try:
            import subprocess
            
            # Use screencapture command
            cmd = ["screencapture", "-x"]  # -x for no sound
            
            if region:
                # Save to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    temp_path = f.name
                
                cmd.extend(["-R", f"{region.x},{region.y},{region.width},{region.height}", temp_path])
                await subprocess.run(cmd, capture_output=True)
                
                with open(temp_path, 'rb') as f:
                    data = f.read()
                
                os.unlink(temp_path)
                return data
            else:
                # Capture to clipboard and read
                cmd.append("-x")  # Clipboard mode
                result = await subprocess.run(cmd, capture_output=True)
                
                # Read from clipboard
                from PIL import Image
                import io
                
                img = Image.open(io.BytesIO(result.stdout))
                buffer = io.BytesIO()
                img.save(buffer, format=self.config.screenshot_format)
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"macOS screenshot failed: {e}")
            return await self._capture_pil(region)
    
    async def _capture_linux(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> bytes:
        """Capture screenshot on Linux."""
        try:
            import subprocess
            
            # Try gnome-screenshot first, then scrot
            cmd = ["gnome-screenshot", "-f", "/tmp/jarvis_screenshot.png"]
            
            try:
                await subprocess.run(cmd, capture_output=True, timeout=5)
            except:
                cmd = ["scrot", "/tmp/jarvis_screenshot.png"]
                await subprocess.run(cmd, capture_output=True)
            
            with open("/tmp/jarvis_screenshot.png", 'rb') as f:
                data = f.read()
            
            os.unlink("/tmp/jarvis_screenshot.png")
            
            # Crop if region specified
            if region:
                from PIL import Image
                img = Image.open(io.BytesIO(data))
                img = img.crop((
                    region.x, region.y,
                    region.x + region.width,
                    region.y + region.height,
                ))
                buffer = io.BytesIO()
                img.save(buffer, format=self.config.screenshot_format)
                return buffer.getvalue()
            
            return data
            
        except Exception as e:
            logger.error(f"Linux screenshot failed: {e}")
            return await self._capture_pil(region)
    
    async def _capture_pil(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> bytes:
        """Fallback capture using PIL."""
        try:
            from PIL import Image, ImageGrab
            
            if region:
                screenshot = ImageGrab.grab(bbox=(
                    region.x, region.y,
                    region.x + region.width,
                    region.y + region.height,
                ))
            else:
                screenshot = ImageGrab.grab()
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format=self.config.screenshot_format)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"PIL screenshot failed: {e}")
            return b""


class OCREngine:
    """
    OCR (Optical Character Recognition) engine.
    
    Extracts text from images.
    """
    
    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._model = None
    
    async def initialize(self) -> bool:
        """Initialize OCR model."""
        try:
            # Try EasyOCR first (better for screenshots)
            try:
                import easyocr
                
                self._model = easyocr.Reader(
                    [self.config.ocr_language],
                    gpu=self.config.use_gpu,
                    verbose=False,
                )
                
                logger.info("EasyOCR initialized")
                return True
                
            except ImportError:
                # Fallback to Tesseract via pytesseract
                try:
                    import pytesseract
                    from PIL import Image
                    
                    # Check if tesseract is installed
                    try:
                        pytesseract.get_tesseract_version()
                        self._model = "tesseract"
                        logger.info("Tesseract OCR initialized")
                        return True
                    except:
                        logger.warning("Tesseract not installed")
                        return False
                        
                except ImportError:
                    logger.warning("No OCR engine available")
                    return False
                    
        except Exception as e:
            logger.error(f"OCR initialization failed: {e}")
            return False
    
    async def extract_text(
        self,
        image_data: bytes,
        region: Optional[ScreenRegion] = None,
    ) -> str:
        """
        Extract text from image.
        
        Args:
            image_data: Image bytes
            region: Optional region to extract from
            
        Returns:
            Extracted text
        """
        if not self._model:
            return ""
        
        try:
            from PIL import Image
            
            # Load image
            img = Image.open(io.BytesIO(image_data))
            
            # Crop if region specified
            if region:
                img = img.crop((
                    region.x, region.y,
                    region.x + region.width,
                    region.y + region.height,
                ))
            
            if self._model == "tesseract":
                import pytesseract
                text = pytesseract.image_to_string(img)
            else:
                # EasyOCR
                results = self._model.readtext(np.array(img))
                text = " ".join(result[1] for result in results)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    async def extract_with_bounding_boxes(
        self,
        image_data: bytes,
    ) -> List[Dict[str, Any]]:
        """
        Extract text with bounding boxes.
        
        Args:
            image_data: Image bytes
            
        Returns:
            List of dicts with text and bounds
        """
        if not self._model or self._model == "tesseract":
            # Tesseract doesn't support bounding boxes easily
            text = await self.extract_text(image_data)
            return [{"text": text, "bounds": None}]
        
        try:
            from PIL import Image
            
            img = Image.open(io.BytesIO(image_data))
            results = self._model.readtext(np.array(img))
            
            items = []
            for result in results:
                bbox, text, confidence = result
                
                if confidence >= self.config.ocr_confidence_threshold:
                    items.append({
                        "text": text,
                        "confidence": confidence,
                        "bounds": bbox,
                    })
            
            return items
            
        except Exception as e:
            logger.error(f"Bounding box extraction failed: {e}")
            return []


class ScreenAnalyzer:
    """
    Analyzes screenshots for UI understanding.
    
    Detects UI elements, understands screen layout.
    """
    
    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._ocr: Optional[OCREngine] = None
    
    async def analyze_screen(
        self,
        image_data: bytes,
    ) -> Dict[str, Any]:
        """
        Analyze a screenshot.
        
        Args:
            image_data: Screenshot bytes
            
        Returns:
            Analysis results
        """
        # Initialize OCR if needed
        if not self._ocr:
            self._ocr = OCREngine(self.config)
            await self._ocr.initialize()
        
        # Extract text
        text = await self._ocr.extract_text(image_data)
        
        # Get detailed extraction
        details = await self._ocr.extract_with_bounding_boxes(image_data)
        
        # Analyze layout
        layout = self._analyze_layout(image_data, details)
        
        return {
            "text": text,
            "elements": details,
            "layout": layout,
            "summary": self._generate_summary(text, layout),
        }
    
    def _analyze_layout(
        self,
        image_data: bytes,
        elements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze screen layout."""
        try:
            from PIL import Image
            
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            
            # Count elements by rough position
            header_count = 0
            sidebar_count = 0
            content_count = 0
            
            for element in elements:
                bounds = element.get("bounds")
                if bounds and len(bounds) >= 2:
                    # Get average Y position
                    avg_y = sum(p[1] for p in bounds) / len(bounds)
                    ratio = avg_y / height
                    
                    if ratio < 0.2:
                        header_count += 1
                    elif ratio > 0.8:
                        sidebar_count += 1
                    else:
                        content_count += 1
            
            return {
                "width": width,
                "height": height,
                "element_count": len(elements),
                "header_elements": header_count,
                "sidebar_elements": sidebar_count,
                "content_elements": content_count,
                "aspect_ratio": width / height,
            }
            
        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")
            return {}
    
    def _generate_summary(self, text: str, layout: Dict[str, Any]) -> str:
        """Generate a summary of the screen."""
        lines = ["Screen Analysis:", ""]
        
        # Text preview
        if text:
            preview = text[:200].replace('\n', ' ')
            lines.append(f"Text detected: \"{preview}...\"")
        else:
            lines.append("No text detected")
        
        # Layout info
        if layout:
            lines.append(f"Dimensions: {layout.get('width', '?')}x{layout.get('height', '?')}")
            lines.append(f"Elements found: {layout.get('element_count', 0)}")
        
        return "\n".join(lines)


class VisionSystem:
    """
    Complete vision system for JARVIS.
    
    Integrates screen capture, OCR, and analysis.
    """
    
    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self._capture = ScreenCapture(self.config)
        self._ocr = OCREngine(self.config)
        self._analyzer = ScreenAnalyzer(self.config)
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the vision system."""
        if self._initialized:
            return True
        
        logger.info("Initializing vision system...")
        
        # Initialize OCR
        if not await self._ocr.initialize():
            logger.warning("OCR not available")
        
        self._initialized = True
        logger.info("Vision system initialized")
        return True
    
    async def capture_and_analyze(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> Dict[str, Any]:
        """
        Capture screen and analyze it.
        
        Args:
            region: Optional region to capture
            
        Returns:
            Analysis results
        """
        # Capture screenshot
        image_data = await self._capture.capture_screen(region)
        
        if not image_data:
            return {"error": "Failed to capture screenshot"}
        
        # Analyze
        return await self._analyzer.analyze_screen(image_data)
    
    async def what_is_on_screen(self) -> str:
        """
        Answer "what is on my screen" question.
        
        Returns:
            Description of screen contents
        """
        analysis = await self.capture_and_analyze()
        
        if "error" in analysis:
            return analysis["error"]
        
        return analysis.get("summary", analysis.get("text", "Nothing detected"))
    
    async def read_text_from_screen(
        self,
        region: Optional[ScreenRegion] = None,
    ) -> str:
        """
        Read all text from screen.
        
        Args:
            region: Optional region to read from
            
        Returns:
            Extracted text
        """
        image_data = await self._capture.capture_screen(region)
        
        if not image_data:
            return "Failed to capture screen"
        
        return await self._ocr.extract_text(image_data)
    
    async def find_text(
        self,
        text: str,
        region: Optional[ScreenRegion] = None,
    ) -> List[ScreenRegion]:
        """
        Find text on screen.
        
        Args:
            text: Text to find
            region: Optional region to search in
            
        Returns:
            List of regions containing the text
        """
        image_data = await self._capture.capture_screen(region)
        
        if not image_data:
            return []
        
        elements = await self._ocr.extract_with_bounding_boxes(image_data)
        
        regions = []
        for element in elements:
            if text.lower() in element.get("text", "").lower():
                bounds = element.get("bounds")
                if bounds and len(bounds) >= 4:
                    # Convert to ScreenRegion
                    xs = [p[0] for p in bounds]
                    ys = [p[1] for p in bounds]
                    
                    regions.append(ScreenRegion(
                        x=int(min(xs)),
                        y=int(min(ys)),
                        width=int(max(xs) - min(xs)),
                        height=int(max(ys) - min(ys)),
                    ))
        
        return regions
    
    def encode_image_base64(self, image_data: bytes) -> str:
        """Encode image as base64 for API calls."""
        return base64.b64encode(image_data).decode("utf-8")
    
    async def close(self) -> None:
        """Clean up resources."""
        self._initialized = False
        logger.info("Vision system closed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get vision system status."""
        return {
            "initialized": self._initialized,
            "ocr_available": self._ocr._model is not None,
            "config": {
                "use_gpu": self.config.use_gpu,
                "ocr_language": self.config.ocr_language,
            },
        }

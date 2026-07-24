"""
JARVIS Phase 3 — Vision Agent.

A dedicated agent for image understanding, screenshot analysis, OCR,
UI understanding, charts, diagrams, PDF pages, desktop analysis,
GUI element detection, and visual reasoning.

Integrates with Browser Agent and Desktop Automation.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VisionAnalysis:
    image_path: str
    description: str = ""
    text: str = ""
    ui_elements: list[dict[str, Any]] | None = None
    objects: list[str] | None = None
    confidence: float = 0.0
    provider: str | None = None
    model: str | None = None


class VisionAgent:
    """
    Dedicated vision agent.

    Wraps existing ``jarvis.vision`` modules and adds agent-level
    orchestration for browser and desktop integration.
    """

    def __init__(self, provider_selector: Any | None = None) -> None:
        self.provider_selector = provider_selector
        self._provider_name: str | None = None
        self._model: str | None = None

    async def initialize(self) -> None:
        if self.provider_selector is not None:
            try:
                selection = await self.provider_selector.select(
                    task_type="vision",
                    requires_vision=True,
                )
                if selection:
                    self._provider_name = selection.provider
                    self._model = selection.model
            except Exception:
                pass

    async def understand_image(self, image_path: str, prompt: str = "Describe this image") -> VisionAnalysis:
        """Understand an image file and return structured analysis."""
        analysis = VisionAnalysis(image_path=image_path, provider=self._provider_name, model=self._model)
        try:
            data_uri = self._encode_image(image_path)
            result = await self._call_vision_model(data_uri, prompt)
            analysis.description = result.get("text", "")
            analysis.text = result.get("text", "")
            analysis.confidence = result.get("confidence", 0.0)
        except Exception as exc:
            logger.debug("understand_image failed: %s", exc)
            analysis.description = f"Error: {exc}"
        return analysis

    async def compare_images(self, image_path_a: str, image_path_b: str, prompt: str = "Compare these two images") -> dict[str, Any]:
        """Compare two images and return structured comparison result."""
        try:
            uri_a = self._encode_image(image_path_a)
            uri_b = self._encode_image(image_path_b)
            result = await self._call_vision_model_with_images([uri_a, uri_b], prompt)
            return {
                "image_a": image_path_a,
                "image_b": image_path_b,
                "comparison": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
            }
        except Exception as exc:
            logger.debug("compare_images failed: %s", exc)
            return {"error": str(exc)}

    async def analyze_screen(self, monitor: int = 0) -> VisionAnalysis:
        """Capture and analyze the current desktop screen."""
        try:
            from jarvis.desktop.automation import get_desktop_automation
            automation = get_desktop_automation()
            path = automation.take_screenshot()
            return await self.understand_image(path, prompt="Analyze this desktop screen. List visible windows, apps, and UI state.")
        except Exception as exc:
            logger.debug("analyze_screen failed: %s", exc)
            return VisionAnalysis(image_path="", description=f"Error: {exc}")

    async def understand_ui(self, screenshot_path: str) -> dict[str, Any]:
        """Perform UI understanding on a screenshot."""
        analysis = await self.understand_image(
            screenshot_path,
            prompt="Identify UI elements, buttons, inputs, menus. Return a structured list of elements.",
        )
        return {
            "image_path": analysis.image_path,
            "description": analysis.description,
            "text": analysis.text,
            "ui_elements": analysis.ui_elements or [],
        }

    async def ocr(self, image_path: str) -> str:
        """Extract text from an image using OCR."""
        analysis = await self.understand_image(image_path, prompt="Extract all visible text from this image.")
        return analysis.text or analysis.description

    async def batch_ocr(self, image_paths: list[str]) -> list[dict[str, Any]]:
        """Process each image through OCR and return list of results."""
        results: list[dict[str, Any]] = []
        for path in image_paths:
            text = await self.ocr(path)
            results.append({"image_path": path, "text": text})
        return results

    async def analyze_chart(self, image_path: str) -> dict[str, Any]:
        """Analyze a chart or diagram and return structured chart data."""
        analysis = await self.understand_image(
            image_path,
            prompt="Analyze this chart. Identify chart type, axes, key data points, and trends.",
        )
        return {
            "chart_type": "unknown",
            "analysis": analysis.description,
            "raw_text": analysis.text,
            "provider": analysis.provider,
            "model": analysis.model,
            "confidence": analysis.confidence,
        }

    async def analyze_pdf_page(self, pdf_path: str, page: int = 0) -> dict[str, Any]:
        """Render a PDF page to image and analyze it."""
        try:
            from jarvis.vision.production import VisionPipeline
            pipeline = VisionPipeline()
            rendered = await pipeline.render_pdf_page(pdf_path, page)
            if rendered and rendered.exists():
                return await self.understand_image(str(rendered), prompt="Extract text and structure from this PDF page.")
        except Exception:
            pass
        return {"page": page, "text": "", "error": "pdf_render_not_available"}

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(path).suffix.lower()
        mime = "image/png" if ext in (".png",) else "image/jpeg"
        return f"data:{mime};base64,{data}"

    async def _call_vision_model(self, data_uri: str, prompt: str) -> dict[str, Any]:
        """Call a multimodal provider."""
        try:
            from jarvis.api.providers import get_provider_manager
            manager = get_provider_manager()
            result = await manager.generate(prompt, images=[data_uri])
            text = getattr(result, "text", "")
            return {"text": text, "confidence": 0.8}
        except Exception:
            pass
        try:
            from jarvis.vision.production import VisionPipeline
            pipeline = VisionPipeline()
            result = await pipeline.analyze(data_uri, prompt)
            return {"text": result or "", "confidence": 0.6}
        except Exception as exc:
            logger.debug("Vision model fallback failed: %s", exc)
            return {"text": "", "confidence": 0.0}

    async def _call_vision_model_with_images(self, data_uris: list[str], prompt: str) -> dict[str, Any]:
        """Call a multimodal provider with multiple images."""
        try:
            from jarvis.api.providers import get_provider_manager
            manager = get_provider_manager()
            result = await manager.generate(prompt, images=data_uris)
            text = getattr(result, "text", "")
            return {"text": text, "confidence": 0.8}
        except Exception:
            pass
        try:
            from jarvis.vision.production import VisionPipeline
            pipeline = VisionPipeline()
            result = await pipeline.analyze(data_uris[0], prompt) if data_uris else ""
            return {"text": result or "", "confidence": 0.6}
        except Exception as exc:
            logger.debug("Vision model fallback failed: %s", exc)
            return {"text": "", "confidence": 0.0}

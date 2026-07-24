"""
JARVIS Image Generation Tool
=============================
Registers image generation capability in the ToolRegistry.

Single Responsibility:
- Receives tool parameters (prompt, width, height, steps).
- Delegates provider resolution & image generation to ProviderManager.
- Returns ToolResult.

Does NOT hardcode providers or perform provider probing.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.api.providers import get_provider_manager
from jarvis.tools.base import PermissionLevel, Tool, ToolResult

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    """
    Generates images by delegating provider discovery and execution
    strictly to ProviderManager.
    """

    name: str = "generate_image"
    description: str = (
        "Generate an image from a text description using an available provider."
    )
    permission_level = PermissionLevel.AUTOMATIC

    KEYWORDS = [
        "generate", "image", "draw", "picture", "photo", "wallpaper",
        "logo", "art", "illustration", "visualize", "create", "paint",
        "render", "sketch", "anime", "portrait", "flux", "dall-e", "sd",
    ]

    @property
    def category(self) -> str:
        return "media"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate",
                },
                "width": {
                    "type": "integer",
                    "description": "Image width in pixels (default 512)",
                    "default": 512,
                },
                "height": {
                    "type": "integer",
                    "description": "Image height in pixels (default 512)",
                    "default": 512,
                },
                "steps": {
                    "type": "integer",
                    "description": "Number of diffusion steps (default 20)",
                    "default": 20,
                },
            },
            "required": ["prompt"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        prompt = input_data.get("prompt", "").strip()
        if not prompt:
            return ToolResult(success=False, output=None, error="No prompt provided")

        width = int(input_data.get("width", 512))
        height = int(input_data.get("height", 512))
        steps = int(input_data.get("steps", 20))

        logger.info("[Executor] Executing ImageGenerationTool for prompt: %r (%dx%d)", prompt[:60], width, height)

        # Delegate provider resolution & generation strictly to ProviderManager
        provider_mgr = get_provider_manager()
        img_path, provider_name = await provider_mgr.generate_image(prompt, width, height, steps)

        if img_path and provider_name:
            logger.info("[Success] Image generated via %s: %s", provider_name, img_path)
            return ToolResult(
                success=True,
                output={
                    "image_path": img_path,
                    "prompt": prompt,
                    "provider": provider_name,
                    "message": f"Image generated successfully using {provider_name}: {img_path}",
                },
            )

        logger.warning("[Failure] Reason: No configured image generation provider is available.")
        return ToolResult(
            success=False,
            output=None,
            error="No configured image generation provider is available.",
        )

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        if not input_data.get("prompt", "").strip():
            return False, "Parameter 'prompt' is required and must be non-empty"
        return True, None

"""
JARVIS Developer Capability SDK
===============================
Provides a clean, declarative Python decorator (@capability) for developers to
create and register enterprise capabilities with zero boilerplate.

Example Usage:
--------------
from jarvis.sdk.capability import capability

@capability(
    name="spotify_play",
    category="media",
    description="Play a song or playlist on Spotify",
    keywords=["spotify", "music", "song", "play", "track"],
    aliases=["play music", "start spotify"],
)
async def play_music(song_name: str, artist: str = "") -> dict:
    # Custom capability execution logic here
    return {"status": "playing", "song": song_name, "artist": artist}
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

from jarvis.events import EventType, get_event_bus
from jarvis.tools.base import PermissionLevel, Tool, ToolResult
from jarvis.tools.registry import get_registry

logger = logging.getLogger(__name__)


def capability(
    name: str,
    category: str = "custom",
    description: str = "",
    version: str = "1.0.0",
    keywords: list[str] | None = None,
    aliases: list[str] | None = None,
    permission_level: PermissionLevel = PermissionLevel.AUTOMATIC,
) -> Callable:
    """
    Decorator that transforms a Python function into an enterprise JARVIS capability.
    """

    def decorator(fn: Callable) -> Callable:
        desc = description or fn.__doc__ or f"Capability {name}"
        kw_list = keywords or [name]
        aliases or [name.replace("_", " ")]

        sig = inspect.signature(fn)
        properties = {}
        required = []

        for p_name, param in sig.parameters.items():
            if p_name in ("self", "cls"):
                continue
            param_type = "string"
            if param.annotation is int:
                param_type = "integer"
            elif param.annotation is float:
                param_type = "number"
            elif param.annotation is bool:
                param_type = "boolean"
            elif param.annotation is dict:
                param_type = "object"
            elif param.annotation is list:
                param_type = "array"

            properties[p_name] = {
                "type": param_type,
                "description": f"Parameter {p_name}",
            }
            if param.default == inspect.Parameter.empty:
                required.append(p_name)

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        class DynamicSDKTool(Tool):
            def __init__(self):
                super().__init__()
                self.name = name
                self.description = desc
                self.permission_level = permission_level
                self.KEYWORDS = kw_list
                self.version = version

            @property
            def category(self) -> str:
                return category

            @property
            def parameters(self) -> dict[str, Any]:
                return schema

            async def execute(
                self, input_data: dict[str, Any], context: dict[str, Any] | None = None
            ) -> ToolResult:
                try:
                    if asyncio.iscoroutinefunction(fn):
                        res = await fn(**input_data)
                    else:
                        res = fn(**input_data)
                    return ToolResult(
                        success=True,
                        output=res if isinstance(res, dict) else {"result": str(res)},
                    )
                except Exception as e:
                    logger.error("[Capability SDK] Error executing %s: %s", name, e)
                    return ToolResult(success=False, output=None, error=str(e))

        tool_instance = DynamicSDKTool()
        get_registry().register(tool_instance)

        # Emit EventType.TOOL on EventBus to trigger CapabilityDiscovery auto-refresh
        get_event_bus().emit(EventType.TOOL, {"action": "registered", "tool": name})

        logger.info("[Capability SDK] Registered dynamic capability: %s (v%s)", name, version)

        return fn

    return decorator

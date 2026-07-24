"""
Live system metrics for the JARVIS dashboard.

Collects CPU, RAM, GPU, Disk, Battery, provider/model, voice status,
memory status, capability count, plugin count, MCP count, and internet status.
"""

from __future__ import annotations

import logging
import platform
import socket
import time
from typing import Any

logger = logging.getLogger(__name__)


async def get_system_metrics() -> dict[str, Any]:
    """Return a snapshot of dashboard metrics."""
    return {
        "cpu": _cpu(),
        "ram": _ram(),
        "gpu": _gpu(),
        "disk": _disk(),
        "battery": _battery(),
        "provider": _provider(),
        "model": _model(),
        "voice": _voice(),
        "memory": _memory_status(),
        "internet": _internet(),
        "capabilities_count": _capability_count(),
        "plugins_count": _plugin_count(),
        "mcp_count": _mcp_count(),
        "platform": platform.system(),
        "timestamp": time.time(),
    }


def _cpu() -> float:
    try:
        import psutil
        return round(psutil.cpu_percent(interval=0.1), 1)
    except Exception:
        return 0.0


def _ram() -> dict[str, Any]:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "percent": round(vm.percent, 1),
            "used_gb": round(vm.used / (1024**3), 1),
            "total_gb": round(vm.total / (1024**3), 1),
        }
    except Exception:
        return {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}


def _gpu() -> dict[str, Any]:
    try:
        import gputil
        gpus = gputil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return {"name": gpu.name, "load": round(gpu.load * 100, 1), "memory_percent": round(gpu.memoryUtil * 100, 1)}
    except Exception:
        pass
    return {"name": "Integrated", "load": 0.0, "memory_percent": 0.0}


def _disk() -> dict[str, Any]:
    try:
        import psutil
        du = psutil.disk_usage(".")
        return {
            "percent": round(du.percent, 1),
            "used_gb": round(du.used / (1024**3), 1),
            "total_gb": round(du.total / (1024**3), 1),
        }
    except Exception:
        return {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}


def _battery() -> dict[str, Any] | None:
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt:
            return {"percent": round(batt.percent, 1), "power_plugged": batt.power_plugged}
    except Exception:
        pass
    return None


def _provider() -> str:
    try:
        from jarvis.api.providers import get_provider_manager
        pm = get_provider_manager()
        if pm.primary_provider:
            return pm.primary_provider.value
    except Exception:
        pass
    return "none"


def _model() -> str:
    try:
        from jarvis.api.providers import get_provider_manager
        pm = get_provider_manager()
        if pm.primary_provider and pm.primary_provider in pm.providers:
            return pm.providers[pm.primary_provider].model
    except Exception:
        pass
    return "none"


def _voice() -> dict[str, Any]:
    try:
        from jarvis.voice.voice_runtime import get_voice_runtime
        rt = get_voice_runtime()
        status = rt.get_status()
        ready = bool(status.get("ready"))
        return {
            "ready": ready,
            "stt": status.get("stt", {}).get("status", "unknown"),
            "tts": status.get("tts", {}).get("status", "unknown"),
            "wake_word": status.get("wake_word", {}).get("status", "unknown"),
        }
    except Exception:
        return {"ready": False, "stt": "unknown", "tts": "unknown", "wake_word": "unknown"}


def _memory_status() -> dict[str, Any]:
    try:
        from jarvis.memory.enhanced import get_enhanced_memory
        mem = get_enhanced_memory()
        count = len(getattr(mem, "memories", []))
        return {"entries": count, "status": "ok" if count > 0 else "empty"}
    except Exception:
        return {"entries": 0, "status": "unknown"}


def _capability_count() -> int:
    try:
        from jarvis.core.capability_router import get_capability_router
        return len(get_capability_router().get_catalog().capabilities)
    except Exception:
        return 0


def _plugin_count() -> int:
    try:
        from jarvis.plugins.plugin_manager import get_plugin_manager
        return len(get_plugin_manager().plugins)
    except Exception:
        return 0


def _mcp_count() -> int:
    try:
        from jarvis.integrations.mcp import get_mcp_registry
        tools = get_mcp_registry().list_tools()
        return sum(len(t) for t in tools.values())
    except Exception:
        return 0


def _internet() -> bool:
    try:
        socket.setdefaulttimeout(1.5)
        socket.create_connection(("8.8.8.8", 53))
        return True
    except Exception:
        return False

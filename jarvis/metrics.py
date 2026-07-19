"""
Live system metrics for the JARVIS dashboard (Feature 3).

Collects CPU, RAM, provider/model, voice status, memory status, and internet
status. Reads from existing modules (provider manager, voice runtime, memory)
and standard libraries only — no backend logic modified.
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
        "provider": _provider(),
        "model": _model(),
        "voice": _voice(),
        "memory": _memory_status(),
        "internet": _internet(),
        "platform": platform.system(),
        "timestamp": time.time(),
    }


def _cpu() -> float:
    try:
        import psutil

        return round(psutil.cpu_percent(interval=0.2), 1)
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


def _internet() -> bool:
    try:
        socket.setdefaulttimeout(1.5)
        socket.create_connection(("8.8.8.8", 53))
        return True
    except Exception:
        return False

"""
Dashboard view helpers for the JARVIS UI.

Provides factory methods that build view-native dictionaries for each
dashboard panel from existing backend state.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DashboardViewFactory:
    """Build standalone view models for each dashboard panel."""

    @staticmethod
    def build_system_panel() -> dict[str, Any]:
        """Return system metrics panel."""
        try:
            from jarvis.core.dashboard import get_dashboard

            return get_dashboard().get_system_health()
        except Exception as exc:
            logger.debug("System panel build error: %s", exc)
            return {"status": "error", "error": str(exc)}

    @staticmethod
    def build_provider_panel() -> dict[str, Any]:
        """Return provider status panel."""
        try:
            providers: list[dict[str, Any]] = []
            try:
                from jarvis.core.provider_manager import get_provider_manager

                pm = get_provider_manager()
                providers = [
                    {
                        "name": name,
                        "status": "available" if getattr(p, "is_available", False) else "unavailable",
                        "priority": getattr(getattr(p, "config", None), "priority", None),
                        "active": name == getattr(pm, "active_provider", None),
                    }
                    for name, p in getattr(pm, "_providers", {}).items()
                ]
            except Exception:
                pass

            try:
                from jarvis.core.provider_health_monitor import get_provider_health_monitor

                health = get_provider_health_monitor().get_status()
                for prov in providers:
                    prov["latency_ms"] = health.get(prov["name"], {}).get("latency_ms", 0.0)
                    prov["success_count"] = health.get(prov["name"], {}).get("success_count", 0)
                    prov["failure_count"] = health.get(prov["name"], {}).get("failure_count", 0)
            except Exception:
                pass

            try:
                from jarvis.core.token_tracker import get_token_tracker

                tracker = get_token_tracker()
                stats = tracker.get_total_stats()
                return {
                    "providers": providers,
                    "total_tokens": stats.get("total_tokens", 0),
                    "total_requests": stats.get("total_requests", 0),
                }
            except Exception:
                return {"providers": providers, "total_tokens": 0, "total_requests": 0}
        except Exception as exc:
            logger.debug("Provider panel build error: %s", exc)
            return {"providers": [], "total_tokens": 0, "total_requests": 0, "error": str(exc)}

    @staticmethod
    def build_memory_panel() -> dict[str, Any]:
        """Return memory usage panel."""
        try:
            from jarvis.core.dashboard import get_dashboard

            snap = get_dashboard().snapshot()
            return {
                "memory_stats": snap.memory_stats,
                "knowledge_graph": snap.knowledge_graph,
                "learning": snap.learning,
            }
        except Exception as exc:
            logger.debug("Memory panel build error: %s", exc)
            return {"memory_stats": {}, "knowledge_graph": {}, "learning": {}, "error": str(exc)}

    @staticmethod
    def build_plugin_panel() -> dict[str, Any]:
        """Return plugin status panel."""
        try:
            from jarvis.core.dashboard import get_dashboard

            snap = get_dashboard().snapshot()
            return {
                "plugins": snap.plugins,
                "count": len(snap.plugins),
            }
        except Exception as exc:
            logger.debug("Plugin panel build error: %s", exc)
            return {"plugins": [], "count": 0, "error": str(exc)}

    @staticmethod
    def build_voice_panel() -> dict[str, Any]:
        """Return voice status panel."""
        try:
            from jarvis.core.dashboard import get_dashboard

            snap = get_dashboard().snapshot()
            voice = snap.voice or {}
            return {
                "voice": voice,
                "status": "ok" if voice.get("listening") or voice.get("speaking") else "idle",
            }
        except Exception as exc:
            logger.debug("Voice panel build error: %s", exc)
            return {"voice": {}, "status": "error", "error": str(exc)}

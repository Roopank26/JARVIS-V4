"""
JARVIS-V4 CAE — System Resource Monitor.

Monitors CPU, RAM, GPU, and disk usage.
Detects high-intensity workloads (gaming, rendering, compiling)
and recommends pausing background evolution.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: float = 0.0
    disk_percent: float = 0.0
    high_intensity: bool = False
    intensity_signals: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "gpu_percent": self.gpu_percent,
            "disk_percent": self.disk_percent,
            "high_intensity": self.high_intensity,
            "intensity_signals": self.intensity_signals,
            "timestamp": self.timestamp,
        }


class SystemResourceMonitor:
    """
    Monitors system resources and detects high-intensity workloads.

    High-intensity signals:
    - CPU > 85% or RAM > 90%
    - GPU > 80% (if available)
    - Known high-intensity processes: game engines, renderers, compilers under heavy load
    """

    GAME_INDICATORS = [
        "valheim",
        "csgo",
        "fortnite",
        "apex",
        "dota2",
        "eldenring",
        "witcher",
        "cyberpunk",
        "minecraft",
        "rocket league",
        "pubg",
        "gta",
        "rdr2",
        "hzd",
        "spiderman",
        "forza",
        "halo",
        "battlenet",
        "steam",
        "epicgameslauncher",
        "origin",
        "riotclient",
        "overwatch",
        "destiny2",
        "diablo",
        "pathofexile",
        "terraria",
        "stardewvalley",
        "valorant",
    ]

    RENDER_INDICATORS = [
        "blender",
        "maya",
        "3dsmax",
        "cinema4d",
        "houdini",
        "nuke",
        "afterfx",
        "premiere",
        "vegas",
        "fusion",
        "zbrush",
        "substance",
        "photoshop",
        "illustrator",
        "indesign",
        "lightroom",
    ]

    COMPILE_INDICATORS = [
        "msbuild",
        "devenv",
        "cl.exe",
        "link.exe",
        "csc.exe",
        "javac",
        "gcc",
        "g++",
        "clang",
        "rustc",
        "go build",
        "dotnet build",
        "cmake",
        "ninja",
        "bazel",
        "msvc",
    ]

    def __init__(self) -> None:
        self._running = False
        self._latest: ResourceSnapshot | None = None
        self._history: list[ResourceSnapshot] = []
        self._max_history = 200

    async def start(self) -> None:
        self._running = True
        logger.info("System resource monitor started")

    async def stop(self) -> None:
        self._running = False
        logger.info("System resource monitor stopped")

    async def sample(self) -> ResourceSnapshot:
        if not self._running:
            return ResourceSnapshot()

        snap = ResourceSnapshot()
        try:
            import asyncio as _asyncio

            import psutil

            snap.cpu_percent = await _asyncio.to_thread(psutil.cpu_percent, 0.1)
            mem = await _asyncio.to_thread(psutil.virtual_memory)
            snap.ram_percent = mem.percent

            disk = await _asyncio.to_thread(psutil.disk_usage, str(Path.home()))
            snap.disk_percent = disk.percent

            gpu = self._sample_gpu()
            if gpu is not None:
                snap.gpu_percent = gpu

        except Exception as exc:
            logger.debug("Resource sampling failed: %s", exc)

        snap.high_intensity, snap.intensity_signals = self._detect_high_intensity(snap)
        self._latest = snap
        self._history.append(snap)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return snap

    def _sample_gpu(self) -> float | None:
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
                if lines:
                    values = [float(line) for line in lines if line.replace(".", "").isdigit()]
                    if values:
                        return max(values)
        except Exception:
            pass
        return None

    def _detect_high_intensity(self, snap: ResourceSnapshot) -> tuple[bool, list[str]]:
        signals: list[str] = []

        if snap.cpu_percent > 85:
            signals.append(f"high_cpu({snap.cpu_percent:.0f}%)")
        if snap.ram_percent > 90:
            signals.append(f"high_ram({snap.ram_percent:.0f}%)")
        if snap.gpu_percent > 80:
            signals.append(f"high_gpu({snap.gpu_percent:.0f}%)")
        if snap.disk_percent > 95:
            signals.append(f"disk_full({snap.disk_percent:.0f}%)")

        if snap.cpu_percent > 85 or snap.ram_percent > 90 or snap.gpu_percent > 80:
            processes = self._inspect_processes()
            signals.extend(processes)

        return bool(signals), signals

    def _inspect_processes(self) -> list[str]:
        signals: list[str] = []
        try:
            import psutil

            for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    cpu = proc.info.get("cpu_percent") or 0.0
                    mem = proc.info.get("memory_percent") or 0.0
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                if any(ind in name for ind in self.GAME_INDICATORS):
                    signals.append(f"game_process:{name}")
                elif any(ind in name for ind in self.RENDER_INDICATORS) and (cpu > 10 or mem > 5):
                    signals.append(f"render_process:{name}")
                elif any(ind in name for ind in self.COMPILE_INDICATORS) and cpu > 20:
                    signals.append(f"compile_process:{name}")
        except Exception as exc:
            logger.debug("Process inspection failed: %s", exc)
        return signals

    def should_pause(self, snap: ResourceSnapshot | None = None) -> bool:
        s = snap or self._latest
        if not s:
            return False
        return s.high_intensity

    def can_resume(self, snap: ResourceSnapshot | None = None) -> bool:
        s = snap or self._latest
        if not s:
            return False
        return (
            s.cpu_percent < 60
            and s.ram_percent < 75
            and s.gpu_percent < 50
            and not s.high_intensity
        )

    def get_latest(self) -> ResourceSnapshot | None:
        return self._latest

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._history[-limit:]]


_resource_monitor_instance: SystemResourceMonitor | None = None


def get_resource_monitor() -> SystemResourceMonitor:
    global _resource_monitor_instance
    if _resource_monitor_instance is None:
        _resource_monitor_instance = SystemResourceMonitor()
    return _resource_monitor_instance


def reset_resource_monitor() -> None:
    global _resource_monitor_instance
    _resource_monitor_instance = None

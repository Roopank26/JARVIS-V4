"""
JARVIS System Diagnostics Module.
Provides comprehensive system health checks.
"""

import platform
from datetime import datetime
from typing import Any


def check_python() -> dict[str, Any]:
    """Check Python installation."""
    import sys

    return {
        "name": "Python",
        "status": "ok",
        "version": platform.python_version(),
        "executable": sys.executable,
    }


def _run_command_check(name: str, command: list[str], version_parser=None) -> dict[str, Any]:
    """Run a command and return diagnostic result."""
    import subprocess

    try:
        result = subprocess.run(command, capture_output=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.decode().strip()
            if version_parser:
                version = version_parser(version)
            return {
                "name": name,
                "status": "ok",
                "version": version,
            }
    except Exception as e:
        return {
            "name": name,
            "status": "error",
            "error": str(e),
        }
    return {"name": name, "status": "not_found"}


def _check_import(name: str, import_name: str, note: str = "installed") -> dict[str, Any]:
    """Check if a module can be imported."""
    try:
        __import__(import_name)
        return {
            "name": name,
            "status": "ok",
            "note": note,
        }
    except ImportError:
        return {"name": name, "status": "not_installed"}


def _check_with_library(
    name: str, library_name: str, check_fn, not_installed_note: str = "not_installed"
) -> dict[str, Any]:
    """Run a check function using an optional library."""
    try:
        lib = __import__(library_name)
        return check_fn(lib)
    except ImportError:
        return {"name": name, "status": "ok", "note": not_installed_note}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}


def check_git() -> dict[str, Any]:
    """Check Git installation."""
    return _run_command_check("Git", ["git", "--version"])


def check_ffmpeg() -> dict[str, Any]:
    """Check FFmpeg installation."""
    return _run_command_check("FFmpeg", ["ffmpeg", "-version"], lambda v: v.split("\n")[0])


def check_ollama() -> dict[str, Any]:
    """Check Ollama installation."""
    try:
        import asyncio
        import threading

        import aiohttp

        result_holder = [None]
        exception_holder = [None]

        def run_check():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:

                    async def _check():
                        try:
                            async with (
                                aiohttp.ClientSession() as session,
                                session.get("http://localhost:11434/api/tags", timeout=5.0) as resp,
                            ):
                                if resp.status == 200:
                                    data = await resp.json()
                                    models = data.get("models", [])
                                    return {
                                        "name": "Ollama",
                                        "status": "ok",
                                        "models": [m["name"] for m in models],
                                        "model_count": len(models),
                                    }
                                else:
                                    return {
                                        "name": "Ollama",
                                        "status": "not_running",
                                        "http_status": resp.status,
                                    }
                        except aiohttp.ClientConnectorError:
                            return {
                                "name": "Ollama",
                                "status": "not_running",
                                "error": "Connection refused - Ollama not running",
                            }
                        except Exception as e:
                            return {"name": "Ollama", "status": "error", "error": str(e)}

                    result_holder[0] = loop.run_until_complete(_check())
                finally:
                    loop.close()
            except Exception as e:
                exception_holder[0] = e

        thread = threading.Thread(target=run_check)
        thread.start()
        thread.join(timeout=10)

        if exception_holder[0]:
            return {"name": "Ollama", "status": "error", "error": str(exception_holder[0])}
        return result_holder[0] or {"name": "Ollama", "status": "error", "error": "No result"}
    except Exception as e:
        return {"name": "Ollama", "status": "error", "error": str(e)}


def check_whisper() -> dict[str, Any]:
    """Check Whisper installation."""
    return _check_import("Whisper", "whisper", "OpenAI Whisper installed")


def check_piper() -> dict[str, Any]:
    """Check Piper TTS installation."""
    return _check_import("Piper", "piper", "Piper TTS installed")


def check_openwakeword() -> dict[str, Any]:
    """Check OpenWakeWord installation."""
    return _check_import("OpenWakeWord", "openwakeword", "OpenWakeWord installed")


def check_microphone() -> dict[str, Any]:
    """Check microphone availability."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        if devices and isinstance(devices, list):
            mics = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if mics:
                return {
                    "name": "Microphone",
                    "status": "ok",
                    "count": len(mics),
                    "default": mics[0].get("name", "Unknown")[:50],
                }
        return {"name": "Microphone", "status": "not_found"}
    except ImportError:
        return {"name": "Microphone", "status": "not_installed"}
    except Exception as e:
        return {"name": "Microphone", "status": "error", "error": str(e)}


def check_speaker() -> dict[str, Any]:
    """Check speaker availability."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        if devices and isinstance(devices, list):
            speakers = [d for d in devices if d.get("max_output_channels", 0) > 0]
            if speakers:
                return {
                    "name": "Speaker",
                    "status": "ok",
                    "count": len(speakers),
                    "default": speakers[0].get("name", "Unknown")[:50],
                }
        return {"name": "Speaker", "status": "not_found"}
    except ImportError:
        return {"name": "Speaker", "status": "not_installed"}
    except Exception as e:
        return {"name": "Speaker", "status": "error", "error": str(e)}


def check_gpu() -> dict[str, Any]:
    """Check GPU availability."""

    def _check(torch):
        if torch.cuda.is_available():
            return {
                "name": "GPU",
                "status": "ok",
                "cuda_available": True,
                "device_count": torch.cuda.device_count(),
                "device_name": (
                    torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None
                ),
            }
        return {
            "name": "GPU",
            "status": "cpu_only",
            "cuda_available": False,
        }

    return _check_with_library("GPU", "torch", _check)


def check_cpu() -> dict[str, Any]:
    """Check CPU information."""

    def _check(psutil):
        return {
            "name": "CPU",
            "status": "ok",
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        }

    return _check_with_library("CPU", "psutil", _check, "psutil not installed")


def check_memory() -> dict[str, Any]:
    """Check memory information."""

    def _check(psutil):
        mem = psutil.virtual_memory()
        return {
            "name": "Memory",
            "status": "ok",
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent,
        }

    return _check_with_library("Memory", "psutil", _check, "psutil not installed")


def check_disk() -> dict[str, Any]:
    """Check disk information."""

    def _check(psutil):
        disk = psutil.disk_usage("/")
        return {
            "name": "Disk",
            "status": "ok",
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent,
        }

    return _check_with_library("Disk", "psutil", _check, "psutil not installed")


def check_internet() -> dict[str, Any]:
    """Check internet connectivity."""
    try:
        import socket

        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return {
            "name": "Internet",
            "status": "ok",
            "note": "Connected",
        }
    except OSError:
        return {"name": "Internet", "status": "offline"}
    except Exception as e:
        return {"name": "Internet", "status": "error", "error": str(e)}


def run_all_diagnostics() -> dict[str, Any]:
    """Run all system diagnostics."""
    checks = {
        "Python": check_python,
        "Git": check_git,
        "FFmpeg": check_ffmpeg,
        "Ollama": check_ollama,
        "Whisper": check_whisper,
        "Piper": check_piper,
        "OpenWakeWord": check_openwakeword,
        "Microphone": check_microphone,
        "Speaker": check_speaker,
        "GPU": check_gpu,
        "CPU": check_cpu,
        "Memory": check_memory,
        "Disk": check_disk,
        "Internet": check_internet,
    }

    results = {}
    for name, check_fn in checks.items():
        try:
            results[name] = check_fn()
        except Exception as e:
            results[name] = {"name": name, "status": "error", "error": str(e)}

    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "checks": results,
    }


def format_diagnostics(diagnostics: dict[str, Any]) -> str:
    """Format diagnostics for display."""
    lines = ["+-- JARVIS System Diagnostics ------------------", "|"]

    # System info
    sys_info = diagnostics.get("system", {})
    lines.append(f"| System: {sys_info.get('platform', 'Unknown')} ({sys_info.get('machine', '')})")
    lines.append(f"| Time: {diagnostics.get('timestamp', 'Unknown')}")
    lines.append("|")

    # Group by status
    checks = diagnostics.get("checks", {})

    # Core tools
    lines.append("| Core Tools:")
    core_tools = ["Python", "Git", "FFmpeg"]
    for name in core_tools:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                version = check.get("version", "")
                if version:
                    lines.append(f"|   [OK] {name}")
                else:
                    lines.append(f"|   [OK] {name}")
            else:
                lines.append(f"|   [FAIL] {name}: {check.get('error', 'not found')}")

    lines.append("|")
    lines.append("| AI & Voice:")
    ai_voice = ["Ollama", "Whisper", "Piper", "OpenWakeWord"]
    for name in ai_voice:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                models_info = ""
                if name == "Ollama" and "models" in check:
                    models_info = f" ({len(check.get('models', []))} models)"
                lines.append(f"|   [OK] {name}{models_info}")
            elif status == "not_running":
                lines.append(f"|   [WARN] {name} (not running)")
            else:
                lines.append(f"|   [FAIL] {name}")

    lines.append("|")
    lines.append("| Audio:")
    audio = ["Microphone", "Speaker"]
    for name in audio:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                info = check.get("default", "")[:30]
                lines.append(f"|   [OK] {name}: {info}")
            else:
                lines.append(f"|   [FAIL] {name}")

    lines.append("|")
    lines.append("| Hardware:")
    hw = ["GPU", "CPU", "Memory", "Disk"]
    for name in hw:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                if name == "GPU":
                    if check.get("cuda_available"):
                        lines.append(f"|   [OK] {name}: {check.get('device_name', 'NVIDIA')[:30]}")
                    else:
                        lines.append(f"|   [WARN] {name}: CPU only")
                elif name == "CPU":
                    cores = check.get("logical_cores", "?")
                    lines.append(f"|   [OK] {name}: {cores} cores")
                elif name == "Memory":
                    total = check.get("total_gb", "?")
                    lines.append(f"|   [OK] {name}: {total} GB")
                elif name == "Disk":
                    free = check.get("free_gb", "?")
                    lines.append(f"|   [OK] {name}: {free} GB free")
            else:
                lines.append(f"|   [?] {name}")

    lines.append("|")
    lines.append("| Connectivity:")
    internet = checks.get("Internet", {})
    if internet.get("status") == "ok":
        lines.append("|   [OK] Internet connected")
    else:
        lines.append("|   [FAIL] Internet offline")

    lines.append("|")
    lines.append("+" + "-" * 46)

    return "\n".join(lines)


async def run_jarvis_doctor() -> str:
    """
    Run comprehensive JARVIS system diagnostics.

    Returns:
        Formatted diagnostics output.
    """
    diagnostics = run_all_diagnostics()
    return format_diagnostics(diagnostics)


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(run_jarvis_doctor()))

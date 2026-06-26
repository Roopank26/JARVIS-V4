"""
JARVIS System Diagnostics Module.
Provides comprehensive system health checks.
"""

import asyncio
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def check_python() -> Dict[str, Any]:
    """Check Python installation."""
    import sys
    return {
        "name": "Python",
        "status": "ok",
        "version": platform.python_version(),
        "executable": sys.executable,
    }


def check_git() -> Dict[str, Any]:
    """Check Git installation."""
    import subprocess
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return {
                "name": "Git",
                "status": "ok",
                "version": result.stdout.decode().strip(),
            }
    except Exception as e:
        return {
            "name": "Git",
            "status": "error",
            "error": str(e),
        }
    return {"name": "Git", "status": "not_found"}


def check_ffmpeg() -> Dict[str, Any]:
    """Check FFmpeg installation."""
    import subprocess
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.decode().split("\n")[0]
            return {
                "name": "FFmpeg",
                "status": "ok",
                "version": version_line,
            }
    except Exception as e:
        return {
            "name": "FFmpeg",
            "status": "error",
            "error": str(e),
        }
    return {"name": "FFmpeg", "status": "not_found"}


def check_ollama() -> Dict[str, Any]:
    """Check Ollama installation."""
    try:
        import aiohttp
        import asyncio
        import threading
        
        result_holder = [None]
        exception_holder = [None]
        
        def run_check():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async def _check():
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get("http://localhost:11434/api/tags", timeout=5.0) as resp:
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
                                        return {"name": "Ollama", "status": "not_running", "http_status": resp.status}
                        except aiohttp.ClientConnectorError:
                            return {"name": "Ollama", "status": "not_running", "error": "Connection refused - Ollama not running"}
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


def check_whisper() -> Dict[str, Any]:
    """Check Whisper installation."""
    try:
        import whisper
        return {
            "name": "Whisper",
            "status": "ok",
            "note": "OpenAI Whisper installed",
        }
    except ImportError:
        return {"name": "Whisper", "status": "not_installed"}


def check_piper() -> Dict[str, Any]:
    """Check Piper TTS installation."""
    try:
        import piper
        return {
            "name": "Piper",
            "status": "ok",
            "note": "Piper TTS installed",
        }
    except ImportError:
        return {"name": "Piper", "status": "not_installed"}


def check_openwakeword() -> Dict[str, Any]:
    """Check OpenWakeWord installation."""
    try:
        import openwakeword
        return {
            "name": "OpenWakeWord",
            "status": "ok",
            "note": "OpenWakeWord installed",
        }
    except ImportError:
        return {"name": "OpenWakeWord", "status": "not_installed"}


def check_microphone() -> Dict[str, Any]:
    """Check microphone availability."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if devices:
            if isinstance(devices, list):
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


def check_speaker() -> Dict[str, Any]:
    """Check speaker availability."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if devices:
            if isinstance(devices, list):
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


def check_gpu() -> Dict[str, Any]:
    """Check GPU availability."""
    try:
        import torch
        if torch.cuda.is_available():
            return {
                "name": "GPU",
                "status": "ok",
                "cuda_available": True,
                "device_count": torch.cuda.device_count(),
                "device_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
            }
        else:
            return {
                "name": "GPU",
                "status": "cpu_only",
                "cuda_available": False,
            }
    except ImportError:
        return {"name": "GPU", "status": "not_installed"}
    except Exception as e:
        return {"name": "GPU", "status": "error", "error": str(e)}


def check_cpu() -> Dict[str, Any]:
    """Check CPU information."""
    try:
        import psutil
        return {
            "name": "CPU",
            "status": "ok",
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        }
    except ImportError:
        return {"name": "CPU", "status": "ok", "note": "psutil not installed"}
    except Exception as e:
        return {"name": "CPU", "status": "error", "error": str(e)}


def check_memory() -> Dict[str, Any]:
    """Check memory information."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "name": "Memory",
            "status": "ok",
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent,
        }
    except ImportError:
        return {"name": "Memory", "status": "ok", "note": "psutil not installed"}
    except Exception as e:
        return {"name": "Memory", "status": "error", "error": str(e)}


def check_disk() -> Dict[str, Any]:
    """Check disk information."""
    try:
        import psutil
        disk = psutil.disk_usage("/")
        return {
            "name": "Disk",
            "status": "ok",
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent,
        }
    except ImportError:
        return {"name": "Disk", "status": "ok", "note": "psutil not installed"}
    except Exception as e:
        return {"name": "Disk", "status": "error", "error": str(e)}


def check_internet() -> Dict[str, Any]:
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


def run_all_diagnostics() -> Dict[str, Any]:
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


def format_diagnostics(diagnostics: Dict[str, Any]) -> str:
    """Format diagnostics for display."""
    lines = ["┌─ JARVIS System Diagnostics ─────────────────", "│"]
    
    # System info
    sys_info = diagnostics.get("system", {})
    lines.append(f"│ System: {sys_info.get('platform', 'Unknown')} ({sys_info.get('machine', '')})")
    lines.append(f"│ Time: {diagnostics.get('timestamp', 'Unknown')}")
    lines.append("│")
    
    # Group by status
    checks = diagnostics.get("checks", {})
    
    # Core tools
    lines.append("│ Core Tools:")
    core_tools = ["Python", "Git", "FFmpeg"]
    for name in core_tools:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                version = check.get("version", "")
                if version:
                    lines.append(f"│   ✓ {name}")
                else:
                    lines.append(f"│   ✓ {name}")
            else:
                lines.append(f"│   ✗ {name}: {check.get('error', 'not found')}")
    
    lines.append("│")
    lines.append("│ AI & Voice:")
    ai_voice = ["Ollama", "Whisper", "Piper", "OpenWakeWord"]
    for name in ai_voice:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                models_info = ""
                if name == "Ollama" and "models" in check:
                    models_info = f" ({len(check.get('models', []))} models)"
                lines.append(f"│   ✓ {name}{models_info}")
            elif status == "not_running":
                lines.append(f"│   ⚠ {name} (not running)")
            else:
                lines.append(f"│   ✗ {name}")
    
    lines.append("│")
    lines.append("│ Audio:")
    audio = ["Microphone", "Speaker"]
    for name in audio:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                info = check.get("default", "")[:30]
                lines.append(f"│   ✓ {name}: {info}")
            else:
                lines.append(f"│   ✗ {name}")
    
    lines.append("│")
    lines.append("│ Hardware:")
    hw = ["GPU", "CPU", "Memory", "Disk"]
    for name in hw:
        if name in checks:
            check = checks[name]
            status = check.get("status", "unknown")
            if status == "ok":
                if name == "GPU":
                    if check.get("cuda_available"):
                        lines.append(f"│   ✓ {name}: {check.get('device_name', 'NVIDIA')[:30]}")
                    else:
                        lines.append(f"│   ⚠ {name}: CPU only")
                elif name == "CPU":
                    cores = check.get("logical_cores", "?")
                    lines.append(f"│   ✓ {name}: {cores} cores")
                elif name == "Memory":
                    total = check.get("total_gb", "?")
                    lines.append(f"│   ✓ {name}: {total} GB")
                elif name == "Disk":
                    free = check.get("free_gb", "?")
                    lines.append(f"│   ✓ {name}: {free} GB free")
            else:
                lines.append(f"│   ? {name}")
    
    lines.append("│")
    lines.append("│ Connectivity:")
    internet = checks.get("Internet", {})
    if internet.get("status") == "ok":
        lines.append("│   ✓ Internet connected")
    else:
        lines.append("│   ✗ Internet offline")
    
    lines.append("│")
    lines.append("└" + "─" * 42)
    
    return "\n".join(lines)


async def run_jarvis_doctor() -> str:
    """
    Run comprehensive JARVIS system diagnostics.
    
    Returns:
        Formatted diagnostics output.
    """
    diagnostics = run_all_diagnostics()
    return format_diagnostics(diagnostics)

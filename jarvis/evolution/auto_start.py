"""
JARVIS-V4 CAE — Auto-start Manager.

Manages OS-level auto-start registration.
Currently supports Windows via registry.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class AutoStartManager:
    def __init__(self, app_name: str = "JARVIS") -> None:
        self.app_name = app_name

    def is_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                return bool(value)
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception as exc:
            logger.debug("Auto-start check failed: %s", exc)
            return False

    def enable(self, executable_path: str | None = None) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            exe = executable_path or self._default_executable()
            if not exe or not Path(exe).exists():
                return False

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, f'"{exe}"')
                return True
            finally:
                winreg.CloseKey(key)
        except Exception as exc:
            logger.debug("Auto-start enable failed: %s", exc)
            return False

    def disable(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, self.app_name)
                return True
            except FileNotFoundError:
                return True
            finally:
                winreg.CloseKey(key)
        except Exception as exc:
            logger.debug("Auto-start disable failed: %s", exc)
            return False

    def _default_executable(self) -> str | None:
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(sys.executable)
        script = Path(sys.argv[0]) if sys.argv else None
        if script and script.exists():
            candidates.append(str(script))
        python_exe = Path(sys.executable)
        if python_exe.exists():
            main_module = Path(__file__).parent.parent / "__main__.py"
            if main_module.exists():
                candidates.append(f'"{python_exe}" "{main_module}"')
        for candidate in candidates:
            if candidate:
                return candidate
        return None


_auto_start_instance: AutoStartManager | None = None


def get_auto_start_manager() -> AutoStartManager:
    global _auto_start_instance
    if _auto_start_instance is None:
        _auto_start_instance = AutoStartManager()
    return _auto_start_instance


def reset_auto_start_manager() -> None:
    global _auto_start_instance
    _auto_start_instance = None

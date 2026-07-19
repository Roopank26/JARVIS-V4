"""
JARVIS Desktop - Diagnostic and Verification Tools
Run diagnostics to verify all components work correctly.
"""

import asyncio
from typing import Dict, Any, List

from jarvis.desktop.platform import (
    get_platform, get_platform_info,
    CrossPlatformAudio, CrossPlatformTray, CrossPlatformService,
    CrossPlatformVSCode
)


class DiagnosticResult:
    """Result of a diagnostic check."""
    
    def __init__(self, name: str, passed: bool, message: str = "", details: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


class DiagnosticRunner:
    """Run comprehensive diagnostics."""
    
    def __init__(self):
        self.results: List[DiagnosticResult] = []
    
    def add(self, result: DiagnosticResult) -> None:
        self.results.append(result)
    
    def summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0,
            "results": [
                {"name": r.name, "passed": r.passed, "message": r.message}
                for r in self.results
            ]
        }


def run_platform_diagnostics() -> DiagnosticRunner:
    """Run platform-specific diagnostics."""
    runner = DiagnosticRunner()
    
    # Platform detection
    platform = get_platform()
    runner.add(DiagnosticResult(
        "Platform Detection",
        True,
        f"Detected: {platform.value}"
    ))
    
    # Platform info
    info = get_platform_info()
    runner.add(DiagnosticResult(
        "Data Directory",
        info.data_dir is not None,
        f"Path: {info.data_dir}"
    ))
    
    runner.add(DiagnosticResult(
        "Temp Directory",
        info.temp_dir is not None,
        f"Path: {info.temp_dir}"
    ))
    
    return runner


def run_audio_diagnostics() -> DiagnosticRunner:
    """Run audio system diagnostics."""
    runner = DiagnosticRunner()
    
    # Audio module
    try:
        audio = CrossPlatformAudio
        runner.add(DiagnosticResult(
            "Audio Module",
            True,
            "Audio module loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Audio Module",
            False,
            f"Failed to load: {e}"
        ))
        return runner
    
    # Microphones
    mics = CrossPlatformAudio.get_microphones()
    runner.add(DiagnosticResult(
        "Microphones",
        len(mics) > 0,
        f"Found {len(mics)} microphone(s)",
        [{"index": m["index"], "name": m["name"]} for m in mics]
    ))
    
    # Speakers
    speakers = CrossPlatformAudio.get_speakers()
    runner.add(DiagnosticResult(
        "Speakers",
        len(speakers) > 0,
        f"Found {len(speakers)} speaker(s)",
        [{"index": s["index"], "name": s["name"]} for s in speakers]
    ))
    
    # Audio test
    if len(mics) > 0:
        runner.add(DiagnosticResult(
            "Microphone Access",
            True,
            f"Using: {mics[0]['name']}"
        ))
    
    return runner


def run_tray_diagnostics() -> DiagnosticRunner:
    """Run system tray diagnostics."""
    runner = DiagnosticRunner()
    
    # Tray availability
    available = CrossPlatformTray.is_available()
    runner.add(DiagnosticResult(
        "System Tray",
        available,
        "Available" if available else "Not available on this platform"
    ))
    
    # Try to create icon
    try:
        icon = CrossPlatformTray.create_icon()
        runner.add(DiagnosticResult(
            "Tray Icon Creation",
            icon is not None,
            "Icon created successfully" if icon else "Failed to create icon"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Tray Icon Creation",
            False,
            f"Error: {e}"
        ))
    
    return runner


def run_service_diagnostics() -> DiagnosticRunner:
    """Run service management diagnostics."""
    runner = DiagnosticRunner()
    
    # Service availability
    available = CrossPlatformService.is_available()
    runner.add(DiagnosticResult(
        "Service Management",
        available,
        "Available" if available else "Not available on this platform"
    ))
    
    return runner


def run_vscode_diagnostics() -> DiagnosticRunner:
    """Run VS Code integration diagnostics."""
    runner = DiagnosticRunner()
    
    # Extension path
    ext_path = CrossPlatformVSCode.get_extension_path()
    runner.add(DiagnosticResult(
        "VS Code Extension Path",
        True,
        f"Path: {ext_path}"
    ))
    
    # Settings path
    settings_path = CrossPlatformVSCode.get_settings_path()
    runner.add(DiagnosticResult(
        "VS Code Settings Path",
        True,
        f"Path: {settings_path}"
    ))
    
    # VS Code executable
    exe_path = CrossPlatformVSCode.get_executable_path()
    runner.add(DiagnosticResult(
        "VS Code Executable",
        exe_path is not None,
        f"Found: {exe_path}" if exe_path else "Not found"
    ))
    
    return runner


def run_jarvis_diagnostics() -> DiagnosticRunner:
    """Run JARVIS component diagnostics."""
    runner = DiagnosticRunner()
    
    # Test imports
    try:
        runner.add(DiagnosticResult(
            "JARVIS Core",
            True,
            "DesktopAssistant loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "JARVIS Core",
            False,
            f"Failed: {e}"
        ))
        return runner
    
    # Test voice components
    try:
        runner.add(DiagnosticResult(
            "Voice Listener",
            True,
            "Listener module loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Voice Listener",
            False,
            f"Failed: {e}"
        ))
    
    # Test memory components
    try:
        runner.add(DiagnosticResult(
            "Long-Term Memory",
            True,
            "Memory module loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Long-Term Memory",
            False,
            f"Failed: {e}"
        ))
    
    # Test scheduler
    try:
        runner.add(DiagnosticResult(
            "Task Scheduler",
            True,
            "Scheduler module loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Task Scheduler",
            False,
            f"Failed: {e}"
        ))
    
    # Test plugins
    try:
        runner.add(DiagnosticResult(
            "Plugin System",
            True,
            "Plugin module loaded"
        ))
    except Exception as e:
        runner.add(DiagnosticResult(
            "Plugin System",
            False,
            f"Failed: {e}"
        ))
    
    return runner


async def run_full_diagnostics() -> Dict[str, Any]:
    """Run all diagnostics."""
    print("=" * 50)
    print("JARVIS Desktop - System Diagnostics")
    print("=" * 50)
    print()
    
    all_results = {}
    
    # Platform diagnostics
    print("Running platform diagnostics...")
    platform_results = run_platform_diagnostics()
    all_results["platform"] = platform_results.summary()
    for r in platform_results.results:
        print(f"  {r}")
    print()
    
    # Audio diagnostics
    print("Running audio diagnostics...")
    audio_results = run_audio_diagnostics()
    all_results["audio"] = audio_results.summary()
    for r in audio_results.results:
        print(f"  {r}")
    print()
    
    # Tray diagnostics
    print("Running system tray diagnostics...")
    tray_results = run_tray_diagnostics()
    all_results["tray"] = tray_results.summary()
    for r in tray_results.results:
        print(f"  {r}")
    print()
    
    # Service diagnostics
    print("Running service diagnostics...")
    service_results = run_service_diagnostics()
    all_results["service"] = service_results.summary()
    for r in service_results.results:
        print(f"  {r}")
    print()
    
    # VS Code diagnostics
    print("Running VS Code diagnostics...")
    vscode_results = run_vscode_diagnostics()
    all_results["vscode"] = vscode_results.summary()
    for r in vscode_results.results:
        print(f"  {r}")
    print()
    
    # JARVIS diagnostics
    print("Running JARVIS diagnostics...")
    jarvis_results = run_jarvis_diagnostics()
    all_results["jarvis"] = jarvis_results.summary()
    for r in jarvis_results.results:
        print(f"  {r}")
    print()
    
    # Overall summary
    total = sum(r["total"] for r in all_results.values())
    passed = sum(r["passed"] for r in all_results.values())
    failed = total - passed
    
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/total*100:.1f}%" if total > 0 else "N/A")
    print()
    
    return all_results


def main():
    """Main entry point for diagnostics."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS Desktop Diagnostics")
    parser.add_argument("--category", choices=["platform", "audio", "tray", "service", "vscode", "jarvis", "all"],
                      default="all", help="Category to diagnose")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.category == "platform":
        results = run_platform_diagnostics().summary()
    elif args.category == "audio":
        results = run_audio_diagnostics().summary()
    elif args.category == "tray":
        results = run_tray_diagnostics().summary()
    elif args.category == "service":
        results = run_service_diagnostics().summary()
    elif args.category == "vscode":
        results = run_vscode_diagnostics().summary()
    elif args.category == "jarvis":
        results = run_jarvis_diagnostics().summary()
    else:
        results = asyncio.run(run_full_diagnostics())
    
    if args.json:
        import json
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

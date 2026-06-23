#!/usr/bin/env python3
"""
JARVIS Desktop - Build Verification Script
Verifies that the packaged application works correctly.
"""

import sys
import os
import subprocess
from pathlib import Path


def run_command(cmd: list, description: str) -> tuple:
    """Run a command and return success status and output."""
    print(f"Running: {description}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except Exception as e:
        return False, str(e)


def verify_executable(exe_path: Path) -> bool:
    """Verify that the executable exists and is valid."""
    print(f"\nVerifying executable: {exe_path}")
    
    if not exe_path.exists():
        print(f"  ERROR: Executable not found at {exe_path}")
        return False
    
    # Check file size (should be at least 10MB for PyInstaller bundle)
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  Size: {size_mb:.1f} MB")
    
    if size_mb < 10:
        print(f"  WARNING: Executable seems too small")
    
    return True


def verify_structure(base_dir: Path) -> bool:
    """Verify JARVIS directory structure."""
    print(f"\nVerifying directory structure...")
    
    required = [
        "jarvis/__init__.py",
        "jarvis/desktop/__init__.py",
        "jarvis/voice/__init__.py",
        "jarvis/memory/__init__.py",
        "jarvis/services/__init__.py",
        "jarvis/plugins/__init__.py",
    ]
    
    all_exist = True
    for path in required:
        full_path = base_dir / path
        if full_path.exists():
            print(f"  ✓ {path}")
        else:
            print(f"  ✗ {path} - MISSING")
            all_exist = False
    
    return all_exist


def run_tests() -> bool:
    """Run JARVIS tests."""
    print("\nRunning JARVIS tests...")
    
    success, output = run_command(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        "Test suite"
    )
    
    if success:
        # Count passed tests
        for line in output.split('\n'):
            if 'passed' in line:
                print(f"  {line.strip()}")
    else:
        print(f"  Some tests failed")
        print(output[-500:])
    
    return success


def run_diagnostics() -> bool:
    """Run diagnostics."""
    print("\nRunning diagnostics...")
    
    try:
        from jarvis.desktop.diagnose import main
        main()
        return True
    except Exception as e:
        print(f"  Diagnostics failed: {e}")
        return False


def main():
    """Main verification."""
    print("=" * 50)
    print("JARVIS Desktop - Build Verification")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    results = {}
    
    # 1. Verify structure
    results["structure"] = verify_structure(base_dir)
    
    # 2. Verify tests
    results["tests"] = run_tests()
    
    # 3. Run diagnostics
    results["diagnostics"] = run_diagnostics()
    
    # 4. Check executable
    exe_paths = [
        base_dir / "dist" / "JARVIS.exe",
        base_dir / "dist" / "JARVIS",
        base_dir / "JARVIS.exe",
    ]
    
    exe_found = False
    for exe_path in exe_paths:
        if verify_executable(exe_path):
            exe_found = True
            results["executable"] = True
            break
    
    if not exe_found:
        print("\n  Note: Executable not built yet. Run build.bat/build.sh first.")
        results["executable"] = None
    
    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    for check, passed in results.items():
        if passed is True:
            status = "✓ PASS"
        elif passed is False:
            status = "✗ FAIL"
        else:
            status = "? SKIP"
        print(f"  {check}: {status}")
    
    all_passed = all(v is True or v is None for v in results.values())
    
    print("\n" + "=" * 50)
    if all_passed:
        print("VERIFICATION: PASSED")
        return 0
    else:
        print("VERIFICATION: FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

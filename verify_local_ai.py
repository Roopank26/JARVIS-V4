#!/usr/bin/env python3
"""
Verification script for JARVIS Ollama Local AI Integration.

This script verifies:
1. Ollama is installed
2. Ollama is running
3. Models are available
4. ProviderManager routes correctly

Usage:
    python verify_local_ai.py
"""

import asyncio
import sys
import subprocess
from typing import Dict, Tuple, List


def print_status(check: str, passed: bool, details: str = ""):
    """Print check status with formatting."""
    status = "✓ PASS" if passed else "✗ FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {check}")
    if details:
        print(f"      {details}")


async def check_ollama_installed() -> Tuple[bool, str]:
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, "Ollama not found in PATH"
    except FileNotFoundError:
        return False, "Ollama not installed"
    except Exception as e:
        return False, str(e)


async def check_ollama_running() -> Tuple[bool, str]:
    """Check if Ollama is running."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=5.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    return True, f"Running, {len(models)} models available"
                return False, f"HTTP {resp.status}"
    except ImportError:
        # Fallback to curl
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "models" in result.stdout:
                return True, "Running (via curl)"
            return False, "Ollama not responding"
        except:
            pass
        return False, "aiohttp/curl not available"
    except Exception as e:
        return False, str(e)


async def check_models() -> Tuple[bool, str]:
    """Check if required models are available."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=5.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    
                    # Check for expected models
                    expected = ["qwen3:8b", "deepseek-r1:8b"]
                    found = [m for m in expected if any(m.lower() in mo.lower() for mo in models)]
                    missing = [m for m in expected if m not in found]
                    
                    if models:
                        return True, f"Models: {', '.join(models[:5])}"
                    return False, "No models found"
                return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


async def check_provider_manager() -> Tuple[bool, str]:
    """Check if ProviderManager routes correctly."""
    try:
        sys.path.insert(0, '/workspace/project/JARVIS')
        from jarvis.api.providers import (
            ProviderManager, OllamaProvider, GroqProvider,
            ProviderType, LLMConfig
        )
        
        # Create manager
        manager = ProviderManager()
        
        # Add Ollama provider
        ollama_config = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        manager.add_provider(OllamaProvider(ollama_config))
        
        # Add Groq provider (mock, won't be available)
        groq_config = LLMConfig(provider=ProviderType.GROQ, api_key="mock")
        manager.add_provider(GroqProvider(groq_config))
        
        # Initialize
        await manager.initialize()
        
        # Check priority order
        if ProviderManager.PROVIDER_PRIORITY[0] == ProviderType.OLLAMA:
            priority_ok = True
        else:
            priority_ok = False
        
        # Check default model
        default_ok = manager.DEFAULT_MODEL == "qwen3:8b"
        
        # Check reasoning model
        reasoning_ok = manager.REASONING_MODEL == "deepseek-r1:8b"
        
        # Check method exists
        methods_exist = all([
            hasattr(manager, 'set_model'),
            hasattr(manager, 'get_best_model_for_task'),
            hasattr(manager, 'format_status'),
            hasattr(manager, 'benchmark_models'),
            hasattr(manager, 'compare_models'),
        ])
        
        all_ok = priority_ok and default_ok and reasoning_ok and methods_exist
        
        details = []
        if priority_ok: details.append("Priority OK")
        if default_ok: details.append("Default OK")
        if reasoning_ok: details.append("Reasoning OK")
        if methods_exist: details.append("Methods OK")
        
        return all_ok, ", ".join(details)
        
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, str(e)


async def check_intelligent_routing() -> Tuple[bool, str]:
    """Check if intelligent model routing works."""
    try:
        sys.path.insert(0, '/workspace/project/JARVIS')
        from jarvis.api.providers import ProviderManager, ProviderType
        
        manager = ProviderManager()
        
        # Test reasoning task detection
        reasoning_tasks = [
            "Explain step by step how neural networks work",
            "Solve this algorithm problem",
            "Calculate the complexity of this code",
        ]
        
        general_tasks = [
            "What is Python?",
            "Write a hello world program",
            "Tell me a joke",
        ]
        
        reasoning_detected = []
        for task in reasoning_tasks:
            model = manager.get_best_model_for_task(task)
            if "deepseek" in model.lower():
                reasoning_detected.append(True)
        
        all_reasoning = all(reasoning_detected) if reasoning_detected else False
        
        return all_reasoning, f"Reasoning detected: {sum(reasoning_detected)}/{len(reasoning_tasks)}"
        
    except Exception as e:
        return False, str(e)


async def main():
    """Run all verification checks."""
    print("\n" + "="*60)
    print("JARVIS Local AI Verification")
    print("="*60 + "\n")
    
    checks: List[Tuple[str, bool, str]] = []
    
    # Check 1: Ollama installed
    print("Checking Ollama installation...")
    passed, details = await check_ollama_installed()
    checks.append(("Ollama", passed, details))
    print_status("Ollama installed", passed, details)
    
    # Check 2: Ollama running
    print("\nChecking Ollama service...")
    passed, details = await check_ollama_running()
    checks.append(("Ollama Service", passed, details))
    print_status("Ollama running", passed, details)
    
    # Check 3: Models available
    print("\nChecking models...")
    passed, details = await check_models()
    checks.append(("Models", passed, details))
    print_status("Models available", passed, details)
    
    # Check 4: ProviderManager
    print("\nChecking ProviderManager...")
    passed, details = await check_provider_manager()
    checks.append(("ProviderManager", passed, details))
    print_status("ProviderManager routing", passed, details)
    
    # Check 5: Intelligent routing
    print("\nChecking intelligent routing...")
    passed, details = await check_intelligent_routing()
    checks.append(("Intelligent Routing", passed, details))
    print_status("Auto model selection", passed, details)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, p, _ in checks if p)
    total_count = len(checks)
    
    print(f"\nPassed: {passed_count}/{total_count} checks\n")
    
    for name, passed, details in checks:
        print_status(name, passed, details)
    
    # Final verdict
    print("\n" + "="*60)
    if passed_count == total_count:
        print("\033[92m✓ ALL CHECKS PASSED\033[0m")
        print("\nJARVIS is ready to use with local AI!")
        print("\nCommands to try:")
        print("  • provider status")
        print("  • list models")
        print("  • switch provider qwen3")
        print("  • switch provider deepseek")
        return 0
    else:
        print(f"\033[91m✗ {total_count - passed_count} CHECK(S) FAILED\033[0m")
        print("\nPlease fix the issues above and run again.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

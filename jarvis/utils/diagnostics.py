"""
JARVIS Diagnostics Module
System checks and health monitoring.
"""

import asyncio
import logging
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.diagnostics")


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[Exception] = None


class DiagnosticCheck:
    """Base class for diagnostic checks."""
    
    def __init__(self, name: str, required: bool = True):
        self.name = name
        self.required = required
    
    async def run(self) -> DiagnosticResult:
        """Run the diagnostic check."""
        raise NotImplementedError
    
    def _create_result(
        self,
        passed: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        duration_ms: float = 0.0,
    ) -> DiagnosticResult:
        return DiagnosticResult(
            name=self.name,
            passed=passed,
            message=message,
            details=details or {},
            duration_ms=duration_ms,
            error=error,
        )


class PythonVersionCheck(DiagnosticCheck):
    """Check Python version compatibility."""
    
    def __init__(self, min_version: tuple = (3, 10)):
        super().__init__("python_version")
        self.min_version = min_version
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        try:
            version = sys.version_info[:3]
            passed = version >= self.min_version
            message = f"Python {version[0]}.{version[1]}.{version[2]}"
            
            if passed:
                message += " (compatible)"
            else:
                message += f" (requires {self.min_version[0]}.{self.min_version[1]}+)"
            
            return self._create_result(
                passed=passed,
                message=message,
                details={
                    "version": f"{version[0]}.{version[1]}.{version[2]}",
                    "min_required": f"{self.min_version[0]}.{self.min_version[1]}",
                },
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message="Python version check failed",
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class PlatformCheck(DiagnosticCheck):
    """Check platform information."""
    
    def __init__(self):
        super().__init__("platform", required=False)
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        try:
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            
            details = {
                "system": system,
                "release": release,
                "version": version,
                "machine": machine,
            }
            
            return self._create_result(
                passed=True,
                message=f"Running on {system} {release}",
                details=details,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message="Platform check failed",
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class DependencyCheck(DiagnosticCheck):
    """Check if required dependencies are available."""
    
    def __init__(self, dependencies: List[str]):
        super().__init__("dependencies")
        self.dependencies = dependencies
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        missing = []
        available = []
        
        for dep in self.dependencies:
            try:
                __import__(dep)
                available.append(dep)
            except ImportError:
                missing.append(dep)
        
        passed = len(missing) == 0
        message = f"{len(available)}/{len(self.dependencies)} dependencies available"
        
        if missing:
            message += f" (missing: {', '.join(missing)})"
        
        return self._create_result(
            passed=passed,
            message=message,
            details={
                "available": available,
                "missing": missing,
            },
            duration_ms=(datetime.now() - start).total_seconds() * 1000,
        )


class OllamaCheck(DiagnosticCheck):
    """Check Ollama availability and models."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__("ollama")
        self.base_url = base_url
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "unknown") for m in data.get("models", [])]
                    
                    return self._create_result(
                        passed=True,
                        message=f"Ollama available with {len(models)} models",
                        details={
                            "base_url": self.base_url,
                            "models": models,
                            "model_count": len(models),
                        },
                        duration_ms=(datetime.now() - start).total_seconds() * 1000,
                    )
                else:
                    return self._create_result(
                        passed=False,
                        message=f"Ollama returned status {response.status_code}",
                        details={"status_code": response.status_code},
                        duration_ms=(datetime.now() - start).total_seconds() * 1000,
                    )
                    
        except ImportError:
            return self._create_result(
                passed=False,
                message="httpx not available (optional)",
                details={"optional": True},
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message=f"Ollama not available at {self.base_url}",
                details={"optional": True},
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class GroqCheck(DiagnosticCheck):
    """Check Groq API configuration."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("groq")
        self.api_key = api_key
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        
        # Check if API key is configured
        if not self.api_key:
            from jarvis.core.config import get_config
            config = get_config()
            self.api_key = config.get("GROQ_API_KEY") or config.get_api_key("groq")
        
        if not self.api_key:
            return self._create_result(
                passed=False,
                message="Groq API key not configured",
                details={"optional": True},
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        
        # Test API connection
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("id", "unknown") for m in data.get("data", [])]
                    
                    return self._create_result(
                        passed=True,
                        message=f"Groq API available with {len(models)} models",
                        details={
                            "models": models[:10],  # Limit to first 10
                            "total_models": len(models),
                        },
                        duration_ms=(datetime.now() - start).total_seconds() * 1000,
                    )
                else:
                    return self._create_result(
                        passed=False,
                        message=f"Groq API returned status {response.status_code}",
                        details={"optional": True},
                        duration_ms=(datetime.now() - start).total_seconds() * 1000,
                    )
                    
        except ImportError:
            return self._create_result(
                passed=False,
                message="httpx not available",
                error=Exception("httpx required for Groq check"),
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message="Groq API check failed",
                details={"optional": True},
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class MemoryCheck(DiagnosticCheck):
    """Check system memory availability."""
    
    def __init__(self, min_free_mb: int = 500):
        super().__init__("system_memory", required=False)
        self.min_free_mb = min_free_mb
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            total_mb = memory.total / (1024 * 1024)
            percent = memory.percent
            
            passed = available_mb >= self.min_free_mb
            
            message = f"{available_mb:.0f}MB available ({percent:.1f}% used)"
            
            return self._create_result(
                passed=passed,
                message=message,
                details={
                    "available_mb": available_mb,
                    "total_mb": total_mb,
                    "percent_used": percent,
                    "min_required_mb": self.min_free_mb,
                },
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except ImportError:
            return self._create_result(
                passed=True,
                message="psutil not available, skipping memory check",
                details={"optional": True},
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message="Memory check failed",
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class DiskSpaceCheck(DiagnosticCheck):
    """Check available disk space."""
    
    def __init__(self, min_free_gb: float = 1.0):
        super().__init__("disk_space", required=False)
        self.min_free_gb = min_free_gb
    
    async def run(self) -> DiagnosticResult:
        start = datetime.now()
        try:
            import psutil
            
            disk = psutil.disk_usage("/")
            available_gb = disk.free / (1024 * 1024 * 1024)
            total_gb = disk.total / (1024 * 1024 * 1024)
            percent = disk.percent
            
            passed = available_gb >= self.min_free_gb
            
            message = f"{available_gb:.2f}GB available ({percent:.1f}% used)"
            
            return self._create_result(
                passed=passed,
                message=message,
                details={
                    "available_gb": available_gb,
                    "total_gb": total_gb,
                    "percent_used": percent,
                    "min_required_gb": self.min_free_gb,
                },
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except ImportError:
            return self._create_result(
                passed=True,
                message="psutil not available, skipping disk check",
                details={"optional": True},
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )
        except Exception as e:
            return self._create_result(
                passed=False,
                message="Disk space check failed",
                error=e,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )


class DiagnosticsRunner:
    """Runs multiple diagnostic checks."""
    
    def __init__(self):
        self._checks: List[DiagnosticCheck] = []
    
    def add_check(self, check: DiagnosticCheck) -> "DiagnosticsRunner":
        """Add a diagnostic check."""
        self._checks.append(check)
        return self
    
    def add_default_checks(self) -> "DiagnosticsRunner":
        """Add default diagnostic checks."""
        self.add_check(PythonVersionCheck((3, 10)))
        self.add_check(PlatformCheck())
        self.add_check(DependencyCheck([
            "asyncio",
            "pathlib",
            "json",
            "logging",
        ]))
        self.add_check(OllamaCheck())
        self.add_check(GroqCheck())
        self.add_check(MemoryCheck())
        self.add_check(DiskSpaceCheck())
        return self
    
    async def run_all(self) -> List[DiagnosticResult]:
        """Run all diagnostic checks."""
        results = []
        
        for check in self._checks:
            try:
                result = await check.run()
                results.append(result)
                
                status = "✓" if result.passed else "✗"
                if check.required or not result.passed:
                    logger.info(f"  {status} {check.name}: {result.message}")
                    
            except Exception as e:
                logger.error(f"  ✗ {check.name}: Failed to run - {e}")
                results.append(DiagnosticResult(
                    name=check.name,
                    passed=False,
                    message=f"Check failed: {e}",
                    error=e,
                ))
        
        return results
    
    def generate_report(self, results: List[DiagnosticResult]) -> str:
        """Generate a formatted report."""
        lines = ["=" * 60, "SYSTEM DIAGNOSTICS REPORT", "=" * 60, ""]
        
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        required_passed = sum(
            1 for r, c in zip(results, self._checks) 
            if r.passed and c.required
        )
        required_total = sum(1 for c in self._checks if c.required)
        
        lines.append(f"Overall: {passed}/{total} checks passed")
        if required_total > 0:
            lines.append(f"Required: {required_passed}/{required_total} passed")
        lines.append("")
        
        for result in results:
            check = next((c for c in self._checks if c.name == result.name), None)
            required = check.required if check else False
            
            status = "✓" if result.passed else "✗"
            req_tag = " [REQUIRED]" if required else " [OPTIONAL]"
            
            lines.append(f"{status} {result.name}{req_tag}: {result.message}")
            
            if result.details and (not result.passed or required):
                for key, value in result.details.items():
                    if key != "optional":
                        lines.append(f"    {key}: {value}")
            
            if result.error and not result.passed:
                lines.append(f"    Error: {result.error}")
            
            lines.append(f"    Duration: {result.duration_ms:.2f}ms")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


async def run_startup_diagnostics() -> List[DiagnosticResult]:
    """Run all startup diagnostic checks."""
    runner = DiagnosticsRunner().add_default_checks()
    return await runner.run_all()

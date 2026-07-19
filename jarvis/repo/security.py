"""
Security Scanner for JARVIS.
Scans code for common security vulnerabilities and issues.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SecurityIssue:
    """A detected security issue."""

    severity: str  # critical, high, medium, low, info
    type: str
    file: str
    line: int
    code: str
    description: str
    recommendation: str


class SecurityScanner:
    """
    Security vulnerability scanner.

    Detects:
    - Hardcoded secrets (passwords, API keys, tokens)
    - SQL injection vulnerabilities
    - Command injection
    - XSS vulnerabilities
    - Insecure dependencies
    - Weak cryptography
    - Unsafe deserialization
    - Path traversal
    """

    # Pattern-based detection rules
    PATTERNS = [
        # Hardcoded secrets
        (
            r'password\s*[=:]\s*["\'](?!{{|ENV|fake|null|test|xxx)[^"\']{3,}["\']',
            "Hardcoded Password",
            "high",
            "Hardcoded passwords can be extracted from source code.",
            "Use environment variables or a secrets manager.",
        ),
        (
            r'api[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']',
            "Hardcoded API Key",
            "high",
            "API keys should not be hardcoded in source code.",
            "Use environment variables or a secrets manager.",
        ),
        (
            r'secret[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']',
            "Hardcoded Secret Key",
            "high",
            "Secret keys should not be hardcoded in source code.",
            "Use environment variables or a secrets manager.",
        ),
        (
            r'access[_-]?token\s*[=:]\s*["\'][^"\']{10,}["\']',
            "Hardcoded Access Token",
            "high",
            "Access tokens should not be hardcoded in source code.",
            "Use environment variables or a secrets manager.",
        ),
        (
            r'private[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']',
            "Hardcoded Private Key",
            "critical",
            "Private keys must never be committed to source control.",
            "Remove immediately and rotate the key.",
        ),
        # Dangerous functions
        (
            r"eval\s*\([^)]*\)\s*;?\s*$",
            "Use of eval()",
            "high",
            "eval() can execute arbitrary code and is a security risk.",
            "Avoid eval(). Use safer alternatives.",
        ),
        (
            r"exec\s*\(",
            "Use of exec()",
            "high",
            "exec() can execute arbitrary code and is a security risk.",
            "Avoid exec(). Use safer alternatives.",
        ),
        (
            r"os\.system\s*\(",
            "Use of os.system()",
            "medium",
            "os.system() can be vulnerable to command injection.",
            "Use subprocess.run() with shell=False.",
        ),
        (
            r"subprocess\s*\.\s*(call|run|spawn|Popen)\s*\([^)]*shell\s*=\s*True",
            "Shell=True in subprocess",
            "high",
            "shell=True can enable command injection attacks.",
            "Use shell=False and pass arguments as a list.",
        ),
        (
            r"pickle\s*\.(load|loads)\s*\(",
            "Unsafe Pickle Deserialization",
            "high",
            "Loading untrusted pickle data can lead to arbitrary code execution.",
            "Use JSON or another safe serialization format.",
        ),
        (
            r"yaml\s*\.(load|safe_load)\s*\([^)]*\)\s*(?!.*Loader=yaml\.SafeLoader)",
            "Unsafe YAML Deserialization",
            "medium",
            "yaml.load() without SafeLoader can execute arbitrary code.",
            "Use yaml.safe_load() or yaml.load(Loader=yaml.SafeLoader).",
        ),
        # SQL Injection
        (
            r'execute\s*\(\s*["\'].*%s',
            "Potential SQL Injection",
            "high",
            "String formatting in SQL queries can lead to SQL injection.",
            "Use parameterized queries.",
        ),
        (
            r"cursor\.execute\s*\([^)]*\+[^)]+\)",
            "Potential SQL Injection",
            "high",
            "String concatenation in SQL queries can lead to SQL injection.",
            "Use parameterized queries.",
        ),
        # Path traversal
        (
            r"open\s*\([^)]*%s[^)]*\)",
            "Potential Path Traversal",
            "medium",
            "String formatting in file paths can lead to path traversal.",
            "Validate and sanitize user input.",
        ),
        (
            r"read\s*\([^)]*request\.",
            "Unvalidated File Read",
            "medium",
            "Reading files based on user input without validation.",
            "Validate that the path is within allowed directories.",
        ),
        # XSS
        (
            r"render_template_string\s*\(",
            "Template Injection (SSTI)",
            "critical",
            "render_template_string can lead to server-side template injection.",
            "Use render_template() with proper template files.",
        ),
        (
            r"dangerouslySetInnerHTML\s*=\s*\{",
            "Potential XSS",
            "high",
            "Setting innerHTML directly can lead to XSS attacks.",
            "Sanitize HTML or use a safe library.",
        ),
        # Weak crypto
        (
            r"hashlib\.(md5|sha1)\s*\(",
            "Weak Hashing Algorithm",
            "medium",
            "MD5 and SHA1 are cryptographically weak.",
            "Use SHA-256 or a stronger algorithm.",
        ),
        (
            r"random\.(choice|randint|shuffle)\s*\(",
            "Insecure Random for Security",
            "medium",
            "random module is not cryptographically secure.",
            "Use secrets module or os.urandom().",
        ),
        # Insecure protocols
        (
            r"http://(?!localhost|127\.0\.0\.1)",
            "Insecure HTTP",
            "low",
            "Using HTTP instead of HTTPS exposes data in transit.",
            "Use HTTPS for all external connections.",
        ),
        (
            r"ftp://",
            "Insecure FTP",
            "low",
            "FTP transmits data without encryption.",
            "Use SFTP or FTPS instead.",
        ),
        # Debug mode
        (
            r"DEBUG\s*=\s*True",
            "Debug Mode Enabled",
            "info",
            "Debug mode should be disabled in production.",
            "Set DEBUG=False in production environments.",
        ),
    ]

    # File-specific rules
    FILE_PATTERNS = [
        (".env", "Environment file", "critical", "Environment files may contain secrets."),
        ("*.key", "Private key file", "critical", "Private keys should not be in source control."),
        ("*.pem", "Certificate file", "high", "Certificates should not be in source control."),
        ("*.log", "Log file", "low", "Log files may contain sensitive information."),
        (
            "*.sqlite",
            "SQLite database",
            "medium",
            "Database files should not be in source control.",
        ),
        ("config.*.py", "Config file with secrets", "high", "Config files may contain secrets."),
    ]

    def __init__(self):
        self.issues: list[SecurityIssue] = []
        self._compiled_patterns: list[tuple] = []

        # Pre-compile patterns for performance
        for pattern, issue_type, severity, desc, rec in self.PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE | re.MULTILINE), issue_type, severity, desc, rec)
            )

    def scan_file(self, file_path: str, content: str | None = None) -> list[SecurityIssue]:
        """Scan a file for security issues."""
        issues = []

        if content is None:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return issues

        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            # Skip comments and strings (basic check)
            if self._is_comment_or_string(line):
                continue

            for pattern, issue_type, severity, desc, rec in self._compiled_patterns:
                if pattern.search(line):
                    issues.append(
                        SecurityIssue(
                            severity=severity,
                            type=issue_type,
                            file=file_path,
                            line=i,
                            code=line.strip()[:100],
                            description=desc,
                            recommendation=rec,
                        )
                    )

        return issues

    def scan_directory(self, directory: str, extensions: list[str] = None) -> list[SecurityIssue]:
        """Scan all files in a directory."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb"]

        all_issues = []

        for ext in extensions:
            for file_path in Path(directory).rglob(f"*{ext}"):
                # Skip common non-source directories
                skip_dirs = {
                    "node_modules",
                    ".git",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "build",
                    "dist",
                    ".next",
                    ".nuxt",
                }
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue

                issues = self.scan_file(str(file_path))
                all_issues.extend(issues)

        self.issues = all_issues
        return all_issues

    def _is_comment_or_string(self, line: str) -> bool:
        """Basic check if line is a comment."""
        stripped = line.strip()
        return (
            stripped.startswith("#")
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
        )

    def get_summary(self) -> dict[str, Any]:
        """Get summary of security issues."""
        summary = {
            "total": len(self.issues),
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            },
            "by_type": {},
            "files_affected": set(),
        }

        for issue in self.issues:
            summary["by_severity"][issue.severity] += 1
            summary["by_type"][issue.type] = summary["by_type"].get(issue.type, 0) + 1
            summary["files_affected"].add(issue.file)

        summary["files_affected"] = list(summary["files_affected"])

        return summary

    def format_report(self) -> str:
        """Format a security report."""
        summary = self.get_summary()

        lines = [
            "[Security Scan Report]",
            "=" * 50,
            "",
            f"Total Issues: {summary['total']}",
            "",
            "By Severity:",
        ]

        for severity in ["critical", "high", "medium", "low", "info"]:
            count = summary["by_severity"].get(severity, 0)
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}[
                severity
            ]
            lines.append(f"  {icon} {severity.upper()}: {count}")

        if summary["total"] > 0:
            lines.extend(["", "Top Issues:"])
            by_type = sorted(summary["by_type"].items(), key=lambda x: x[1], reverse=True)
            for issue_type, count in by_type[:5]:
                lines.append(f"  • {issue_type}: {count}")

        lines.extend(["", "Files Affected:"])
        for file in summary["files_affected"][:10]:
            lines.append(f"  • {file}")

        if len(summary["files_affected"]) > 10:
            lines.append(f"  ... and {len(summary['files_affected']) - 10} more")

        return "\n".join(lines)

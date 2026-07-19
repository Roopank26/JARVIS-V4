"""
Integrations module for JARVIS.
Provides third-party tool integrations (VS Code, etc.).
"""

from jarvis.integrations.vscode import VSCodeBridge, VSCodeCommands

__all__ = ["VSCodeBridge", "VSCodeCommands"]

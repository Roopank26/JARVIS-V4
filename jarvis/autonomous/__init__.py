"""
JARVIS Autonomous tasks package.

Provides the task scheduler and approval-gate machinery for
autonomous multi-step operations.
"""

from __future__ import annotations

from jarvis.autonomous.task_scheduler import ApprovalGates, TaskPipeline

__all__ = [
    "ApprovalGates",
    "TaskPipeline",
]

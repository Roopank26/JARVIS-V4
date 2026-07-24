"""
JARVIS Phase 3 — Multi-Agent Collaboration Framework.

Extends the existing ``agents/multi_agent.py`` system with:
- Delegation
- Assistance requests
- Structured context exchange
- Intermediate result sharing
- Conflict resolution
- Retry with backoff
- Output merging
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.context_bus import ContextBus, get_context_bus
from jarvis.events import EventBus, EventType

logger = logging.getLogger(__name__)


@dataclass
class CollaborationRequest:
    """A request from one agent to another."""

    request_id: str
    sender: str
    receiver: str
    capability: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    ttl_s: float = 30.0
    created_at: float = field(default_factory=time.time)


@dataclass
class CollaborationResult:
    """Result from a delegated task."""

    request_id: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentCollaboration:
    """
    Collaboration layer for JARVIS multi-agent system.

    Allows agents to delegate work, request assistance, exchange structured
    context, share intermediate results, resolve conflicts, retry failed
    subtasks, and merge outputs.
    """

    def __init__(
        self,
        bus: EventBus | None = None,
        context_bus: ContextBus | None = None,
    ) -> None:
        self._bus = bus
        self._context = context_bus or get_context_bus()
        self._pending: dict[str, asyncio.Future] = {}
        self._history: list[CollaborationResult] = []
        self._default_timeout = 30.0

    async def delegate(
        self,
        agent_name: str,
        capability: str,
        payload: dict[str, Any],
        timeout: float | None = None,
        retries: int = 1,
        backoff: float = 0.5,
    ) -> CollaborationResult:
        """
        Delegate a capability request to another agent.

        Supports automatic retry with exponential backoff on failure.
        """
        request_id = uuid.uuid4().hex[:12]
        request = CollaborationRequest(
            request_id=request_id,
            sender="orchestrator",
            receiver=agent_name,
            capability=capability,
            payload=payload,
            ttl_s=timeout or self._default_timeout,
        )
        start = time.perf_counter()
        last_error = None

        for attempt in range(1, retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._execute_delegation(request),
                    timeout=request.ttl_s,
                )
                duration = (time.perf_counter() - start) * 1000.0
                collab_result = CollaborationResult(
                    request_id=request_id,
                    success=result.get("success", False),
                    output=result.get("output"),
                    error=result.get("error"),
                    duration_ms=duration,
                    retries=attempt - 1,
                )
                self._history.append(collab_result)
                return collab_result
            except TimeoutError:
                last_error = "timeout"
                await asyncio.sleep(backoff * (2 ** (attempt - 1)))
            except Exception as exc:
                last_error = str(exc)
                await asyncio.sleep(backoff * (2 ** (attempt - 1)))

        duration = (time.perf_counter() - start) * 1000.0
        collab_result = CollaborationResult(
            request_id=request_id,
            success=False,
            error=last_error or "delegation failed",
            duration_ms=duration,
            retries=retries - 1,
        )
        self._history.append(collab_result)
        return collab_result

    async def request_assistance(
        self,
        capability: str,
        context: dict[str, Any],
        preferred_agents: list[str] | None = None,
    ) -> CollaborationResult:
        """
        Ask any capable agent for assistance on a subtask.

        The system selects the best available agent for the capability.
        """
        candidates = preferred_agents or self._find_capable_agents(capability)
        if not candidates:
            return CollaborationResult(
                request_id=uuid.uuid4().hex[:12],
                success=False,
                error=f"No agents found for capability: {capability}",
            )

        for agent in candidates:
            result = await self.delegate(
                agent_name=agent,
                capability=capability,
                payload=context,
                retries=1,
            )
            if result.success:
                return result
        return CollaborationResult(
            request_id=uuid.uuid4().hex[:12],
            success=False,
            error="All candidate agents failed",
        )

    async def exchange_context(
        self,
        source_agent: str,
        target_agent: str,
        data: dict[str, Any],
        envelope_type: str = "context",
    ) -> Any:
        """Exchange structured context between two agents."""
        try:
            envelope = self._context.publish(
                event_type=envelope_type,
                task_id=data.get("task_id"),
                goal_id=data.get("goal_id"),
                data=data,
            )
            if self._bus is not None:
                self._bus.emit(
                    EventType.ACTIVITY,
                    {
                        "actor": source_agent,
                        "action": "context_exchange",
                        "target": target_agent,
                        "envelope_id": envelope.id,
                    },
                )
            return envelope
        except Exception as exc:
            logger.debug("Context exchange failed: %s", exc)
            return None

    def share_intermediate(self, step: int, data: dict[str, Any]) -> None:
        """Share intermediate results with all subscribers."""
        try:
            self._context.publish(
                event_type="intermediate",
                task_id=data.get("task_id"),
                data={"step": step, **data},
            )
        except Exception as exc:
            logger.debug("Intermediate share failed: %s", exc)

    def resolve_conflict(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve a conflict between agent outputs.

        Heuristic priority:
        1. Higher confidence wins
        2. More sources agree
        3. fresher evidence wins
        """
        candidates = conflict.get("candidates", [])
        if not candidates:
            return conflict

        def score(c: dict[str, Any]) -> tuple:
            return (
                c.get("confidence", 0.0),
                c.get("source_count", 0),
                c.get("timestamp", 0.0),
            )

        best = max(candidates, key=score)
        return {"resolved": True, "winner": best, "strategy": "heuristic_score"}

    def merge_outputs(self, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Merge multiple agent outputs into a unified result.

        Deduplicates by URL/title/source, preserves unique key findings.
        """
        merged: dict[str, Any] = {
            "combined": True,
            "sources": [],
            "key_findings": [],
            "errors": [],
        }
        seen = set()
        for out in outputs:
            if not out.get("success", False):
                merged["errors"].append(out.get("error"))
                continue
            for src in out.get("sources", []):
                key = src.get("url") or src.get("title")
                if key and key not in seen:
                    seen.add(key)
                    merged["sources"].append(src)
            for finding in out.get("key_findings", []):
                if finding not in merged["key_findings"]:
                    merged["key_findings"].append(finding)
        return merged

    async def retry_failed_subtasks(
        self,
        failed_tasks: list[dict[str, Any]],
        executor: Any,
        max_retries: int = 2,
    ) -> list[dict[str, Any]]:
        """Retry a batch of failed subtasks with backoff."""
        results = []
        for task in failed_tasks:
            attempt = 0
            while attempt < max_retries:
                attempt += 1
                try:
                    result = await executor.execute(
                        task.get("tool", "bash"),
                        task.get("parameters", {}),
                    )
                    if getattr(result, "success", False):
                        results.append({"task": task, "retried": True, "result": result})
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
            else:
                results.append({"task": task, "retried": False})
        return results

    def _find_capable_agents(self, capability: str) -> list[str]:
        """Find agents that advertise a given capability."""
        candidates = []
        try:
            from jarvis.core.agent_registry import get_agent_registry
            registry = get_agent_registry()
            for name in registry.list_available():
                meta = registry.get_metadata(name)
                if meta and capability in meta.capabilities:
                    candidates.append(name)
        except Exception:
            pass
        return candidates

    async def _execute_delegation(self, request: CollaborationRequest) -> dict[str, Any]:
        """Execute a delegation to the target agent."""
        try:
            from jarvis.core.agent_registry import get_agent_registry
            registry = get_agent_registry()
            agent = registry.get(request.receiver)
            if agent is None:
                return {"success": False, "error": f"Agent not found: {request.receiver}"}
            if asyncio.iscoroutinefunction(getattr(agent, "process", None)):
                output = await agent.process(request.payload)
            else:
                output = agent.process(request.payload)
            return {"success": True, "output": output}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent collaboration history."""
        return [
            {
                "request_id": r.request_id,
                "success": r.success,
                "error": r.error,
                "duration_ms": r.duration_ms,
                "retries": r.retries,
            }
            for r in self._history[-limit:]
        ]

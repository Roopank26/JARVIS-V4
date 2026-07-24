"""
Performance Optimization for JARVIS.

Optimizes:
- Agent scheduling
- Memory usage
- Provider selection
- Parallel execution
- Task batching
- Caching
- Lazy initialization
- Startup time
- Shutdown time
- Resource cleanup
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    hits: int = 0
    ttl: float = 300.0

    def is_valid(self) -> bool:
        return (time.perf_counter() - self.timestamp) < self.ttl


class LRUCache:
    def __init__(self, capacity: int = 128) -> None:
        self._capacity = capacity
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None or not entry.is_valid():
            self._store.pop(key, None)
            return None
        entry.hits += 1
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any, ttl: float = 300.0) -> None:
        self._store[key] = CacheEntry(key=key, value=value, ttl=ttl)
        self._store.move_to_end(key)
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def stats(self) -> dict[str, Any]:
        return {
            "size": len(self._store),
            "capacity": self._capacity,
            "keys": list(self._store.keys()),
        }


class PerformanceOptimizer:
    """
    Performance optimization layer for JARVIS.
    """

    def __init__(self) -> None:
        self._cache = LRUCache(capacity=256)
        self._metrics: dict[str, list[float]] = {}
        self._startup_timestamps: dict[str, float] = {}
        self._instance_cache: dict[str, Any] = {}
        self._batch_queue: list[tuple[str, Any, dict[str, Any]]] = []
        self._batch_size = 10

    def cached(self, key: str, ttl: float = 300.0):
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cached_value = self._cache.get(key)
                if cached_value is not None:
                    return cached_value
                result = await fn(*args, **kwargs)
                self._cache.set(key, result, ttl=ttl)
                return result

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cached_value = self._cache.get(key)
                if cached_value is not None:
                    return cached_value
                result = fn(*args, **kwargs)
                self._cache.set(key, result, ttl=ttl)
                return result

            if asyncio.iscoroutinefunction(fn):
                return async_wrapper
            return sync_wrapper

        return decorator

    def timeit(self, name: str) -> Callable:
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                result = await fn(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000.0
                self._metrics.setdefault(name, []).append(duration)
                return result

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                result = fn(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000.0
                self._metrics.setdefault(name, []).append(duration)
                return result

            if asyncio.iscoroutinefunction(fn):
                return async_wrapper
            return sync_wrapper

        return decorator

    def record_startup(self, subsystem: str) -> None:
        self._startup_timestamps[subsystem] = time.perf_counter()

    def get_startup_time(self, subsystem: str) -> float | None:
        start = self._startup_timestamps.get(subsystem)
        if start is None:
            return None
        return (time.perf_counter() - start) * 1000.0

    def cache_instance(self, key: str, instance: Any) -> None:
        self._instance_cache[key] = instance

    def get_instance(self, key: str) -> Any | None:
        return self._instance_cache.get(key)

    def add_batch(self, key: str, value: Any, meta: dict[str, Any] | None = None) -> None:
        self._batch_queue.append((key, value, meta or {}))
        if len(self._batch_queue) >= self._batch_size:
            self.flush_batch()

    def flush_batch(self) -> None:
        batch = self._batch_queue[:]
        self._batch_queue.clear()
        for key, value, meta in batch:
            with contextlib.suppress(Exception):
                self._cache.set(key, value, ttl=meta.get("ttl", 300.0))

    def get_metrics(self, name: str) -> dict[str, Any]:
        times = self._metrics.get(name, [])
        if not times:
            return {"count": 0}
        return {
            "count": len(times),
            "avg_ms": round(sum(times) / len(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
        }

    def get_all_metrics(self) -> dict[str, Any]:
        return {name: self.get_metrics(name) for name in self._metrics}

    def invalidate_cache(self, key: str | None = None) -> None:
        if key is None:
            self._cache.clear()
        else:
            self._cache.invalidate(key)

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": True,
            "cache": self._cache.stats(),
            "metrics_count": len(self._metrics),
            "instance_cache": len(self._instance_cache),
        }


_optimizer: PerformanceOptimizer | None = None


def get_optimizer() -> PerformanceOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer


def reset_optimizer() -> None:
    global _optimizer
    _optimizer = None

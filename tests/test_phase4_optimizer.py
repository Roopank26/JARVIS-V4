"""
Tests for JARVIS Phase 4 — Performance Optimizer.
"""


def test_lru_cache_get_set():
    from jarvis.performance.optimizer import LRUCache
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("missing") is None


def test_lru_cache_eviction():
    from jarvis.performance.optimizer import LRUCache
    cache = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_cache_invalidate():
    from jarvis.performance.optimizer import LRUCache
    cache = LRUCache()
    cache.set("x", 42)
    cache.invalidate("x")
    assert cache.get("x") is None


def test_lru_cache_stats():
    from jarvis.performance.optimizer import LRUCache
    cache = LRUCache()
    stats = cache.stats()
    assert "size" in stats
    assert stats["size"] == 0


def test_optimizer_singleton():
    from jarvis.performance.optimizer import get_optimizer, reset_optimizer
    opt = get_optimizer()
    assert opt is get_optimizer()
    reset_optimizer()


def test_optimizer_cached():
    from jarvis.performance.optimizer import get_optimizer, reset_optimizer
    opt = get_optimizer()
    opt.invalidate_cache()
    reset_optimizer()

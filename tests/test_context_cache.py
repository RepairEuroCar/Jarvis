import time

from core.context_cache import ContextCache


def test_cache_set_get_and_expire():
    cache = ContextCache()
    cache.set("foo", "bar", ttl=0.1)
    assert cache.get("foo") == "bar"
    time.sleep(0.12)
    assert cache.get("foo") is None


def test_cache_eviction():
    cache = ContextCache(max_size=1)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") is None
    assert cache.get("b") == 2

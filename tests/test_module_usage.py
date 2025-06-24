import asyncio

import pytest

from core.metrics.module_usage import track_usage, get_module_stats
from modules.module_usage import _format_stats


@track_usage("sync_mod")
def _sync_func(x):
    return x + 1


@track_usage("async_mod")
async def _async_func(x):
    await asyncio.sleep(0)
    return x + 2


@track_usage("error_mod")
def _error_func():
    raise ValueError("boom")


@pytest.mark.asyncio
async def test_track_usage_records_stats():
    assert _sync_func(1) == 2
    assert await _async_func(1) == 3
    with pytest.raises(ValueError):
        _error_func()

    stats = get_module_stats()
    assert stats["sync_mod"]["calls"] == 1
    assert stats["async_mod"]["calls"] == 1
    assert stats["error_mod"]["errors"] == 1
    assert stats["sync_mod"]["errors"] == 0
    assert stats["async_mod"]["errors"] == 0


def test_format_stats():
    stats = {"m": {"calls": 2, "errors": 1, "avg_duration": 0.1}}
    out = _format_stats(stats)
    assert "m:" in out
    assert "calls=2" in out

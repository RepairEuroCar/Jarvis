import logging

from core.profiler import ModuleProfiler


def test_profiler_records_stats_and_warns(caplog):
    profiler = ModuleProfiler()

    def heavy_func():
        _ = bytearray(11 * 1024 * 1024)
        return True

    with caplog.at_level(logging.WARNING):
        wrapped = profiler.profile("dummy", "heavy_func")(heavy_func)
        wrapped()

    stats = profiler.get_stats()
    assert stats["dummy"]["heavy_func"]["peak_memory_kb"] > 10 * 1024
    assert any("Profiler" in r.message for r in caplog.records)


from core.events import register_event_emitter
from core.flags import FlagManager


def test_flag_manager_records_errors_and_flags():
    events = []
    register_event_emitter(lambda n, d: events.append((n, d)))
    fm = FlagManager(error_threshold=2, window=1)
    fm.record_error("demo", Exception("boom"))
    assert not fm.is_flagged("demo")
    fm.record_error("demo", Exception("boom"))
    assert fm.is_flagged("demo")
    assert any(e[0] == "ModuleAnomalyFlagged" for e in events)
    fm.clear_flag("demo")
    assert not fm.is_flagged("demo")

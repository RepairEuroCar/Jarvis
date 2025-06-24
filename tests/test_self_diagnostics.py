import time

from core.events import register_event_emitter
from core.module_registry import register_module_supplier
from core.flags import default_flag_manager
from modules.self_diagnostics import SelfDiagnostics


class DummyModule:
    def __init__(self):
        self.called = False
        self.name = "dummy"

    def get_health_metrics(self):
        self.called = True
        return {"response_time": 300, "threshold": 200, "error_rate": 0}


def test_self_diagnostics_emits_event():
    events = []
    register_event_emitter(lambda name, data: events.append((name, data)))
    module = DummyModule()
    register_module_supplier(lambda: [module])

    diag = SelfDiagnostics(interval=0.1)
    diag.start()
    time.sleep(0.25)
    diag.stop()

    assert module.called
    assert any(e[0] == "ModuleDegradationDetected" for e in events)


def test_self_diagnostics_flags_module():
    events = []
    register_event_emitter(lambda n, d: events.append((n, d)))
    module = DummyModule()
    default_flag_manager.clear_flag("dummy")
    register_module_supplier(lambda: [module])

    diag = SelfDiagnostics(interval=0.1)
    diag.start()
    time.sleep(0.25)
    diag.stop()

    assert default_flag_manager.is_flagged("dummy")
    assert any(e[0] == "ModuleAnomalyFlagged" for e in events)

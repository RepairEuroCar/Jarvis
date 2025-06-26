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


class FailingModule:
    def __init__(self):
        self.name = "failing"
        self.health_calls = 0
        self.reconnects = 0

    def get_health_metrics(self):
        return {"response_time": 0, "threshold": 1, "error_rate": 0}

    async def health_check(self):
        self.health_calls += 1
        return self.health_calls > 1

    async def reconnect(self):
        self.reconnects += 1


def test_self_diagnostics_attempts_reconnect():
    register_event_emitter(lambda *a, **k: None)
    module = FailingModule()
    register_module_supplier(lambda: [module])

    diag = SelfDiagnostics(interval=0.05, backoff_base=0.01, backoff_max=0.05)
    diag.start()
    time.sleep(0.15)
    diag.stop()

    assert module.reconnects == 1

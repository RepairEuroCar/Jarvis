import os
import time

from core.events import register_event_emitter
from core.module_registry import register_module_supplier
from core.flags import default_flag_manager
from modules.resource_limiter import ResourceLimiter


class DummyModule:
    def __init__(self) -> None:
        self.name = "dummy"
        self.pid = os.getpid()

    def get_pid(self) -> int:
        return self.pid

    def get_resource_quota(self) -> dict:
        return {"memory": 0, "cpu": 100}


def test_resource_limiter_emits_warning():
    events = []
    register_event_emitter(lambda n, d: events.append((n, d)))
    module = DummyModule()
    register_module_supplier(lambda: [module])

    limiter = ResourceLimiter(interval=0.1)
    limiter.start()
    time.sleep(0.3)
    limiter.stop()

    assert any(e[0] == "ResourceLimitWarning" for e in events)


def test_resource_limiter_flags_module():
    events = []
    register_event_emitter(lambda n, d: events.append((n, d)))
    module = DummyModule()
    default_flag_manager.clear_flag("dummy")
    register_module_supplier(lambda: [module])

    limiter = ResourceLimiter(interval=0.1)
    limiter.start()
    time.sleep(0.3)
    limiter.stop()

    assert default_flag_manager.is_flagged("dummy")
    assert any(e[0] == "ModuleAnomalyFlagged" for e in events)


def test_resource_limiter_skips_module_without_pid():
    events = []
    register_event_emitter(lambda n, d: events.append((n, d)))

    class NoPid:
        name = "nopid"

        def get_resource_quota(self) -> dict:
            return {"memory": 0, "cpu": 0}

    register_module_supplier(lambda: [NoPid()])

    limiter = ResourceLimiter(interval=0.1)
    limiter.start()
    time.sleep(0.2)
    limiter.stop()

    assert events == []

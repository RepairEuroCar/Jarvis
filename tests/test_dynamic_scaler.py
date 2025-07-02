import time

import psutil

from jarvis.core.module_manager import ModuleConfig, ModuleManager, ModuleState
from modules.dynamic_scaler import DynamicScaler


class DummyJarvis:
    pass


def test_dynamic_scaler_pauses_and_resumes(monkeypatch):
    manager = ModuleManager(DummyJarvis())
    manager.modules = {"a": object(), "b": object()}
    manager.module_configs = {
        "a": ModuleConfig(priority=10),
        "b": ModuleConfig(priority=60),
    }
    manager.module_states = {"a": ModuleState.LOADED, "b": ModuleState.LOADED}

    paused = []
    resumed = []

    async def fake_pause(name):
        paused.append(name)
        manager.module_states[name] = ModuleState.PAUSED
        manager.modules.pop(name, None)
        return True

    async def fake_resume(name):
        resumed.append(name)
        manager.module_states[name] = ModuleState.LOADED
        manager.modules[name] = object()
        return True

    monkeypatch.setattr(manager, "pause_module", fake_pause)
    monkeypatch.setattr(manager, "resume_module", fake_resume)

    metrics = {"cpu": 0.0, "mem": 0.0}

    def fake_cpu_percent(interval=None):
        return metrics["cpu"]

    class Mem:
        def __init__(self, p):
            self.percent = p

    def fake_virtual_memory():
        return Mem(metrics["mem"])

    monkeypatch.setattr(psutil, "cpu_percent", fake_cpu_percent)
    monkeypatch.setattr(psutil, "virtual_memory", fake_virtual_memory)

    scaler = DynamicScaler(manager, interval=0.1, cpu_threshold=50, memory_threshold=50)
    scaler.start()

    metrics["cpu"] = 80
    time.sleep(0.3)
    metrics["cpu"] = 10
    metrics["mem"] = 10
    time.sleep(0.3)
    scaler.stop()

    assert "b" in paused
    assert "b" in resumed

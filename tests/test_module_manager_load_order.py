import asyncio
import sys
import types

import pytest

from jarvis.core.module_manager import ModuleConfig, ModuleManager


class DummyJarvis:
    pass


@pytest.mark.asyncio
async def test_load_modules_respects_priority(monkeypatch):
    modules = {}
    load_order = []
    for name, pr in [("a", 20), ("b", 10), ("c", 30)]:
        mod = types.ModuleType(name)
        mod.__version__ = "1.0.0"

        async def setup(jarvis, config, _name=name):
            await asyncio.sleep(0.01)
            load_order.append(_name)
            return object()

        mod.setup = setup
        sys.modules[f"jarvis.modules.{name}"] = mod
        modules[name] = ModuleConfig(enabled=True, priority=pr)

    manager = ModuleManager(DummyJarvis())
    await manager.load_modules(modules)

    assert list(manager.module_states.keys()) == ["b", "a", "c"]
    assert load_order == ["b", "a", "c"]

import sys
import types

import pytest

from jarvis.core.module_manager import ModuleManager, JarvisModule
from core.profiler import default_profiler


class DummyJarvis:
    pass


class DummyModule(JarvisModule):
    async def setup(self, jarvis, config):
        return True

    async def cleanup(self):
        pass


async def dummy_setup(jarvis, config):
    return DummyModule()


@pytest.mark.asyncio
async def test_load_module_profiles_init(monkeypatch):
    mod = types.ModuleType("dummy_mod")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    sys.modules["jarvis.modules.dummy_mod"] = mod

    manager = ModuleManager(DummyJarvis())
    default_profiler.stats.clear()

    result = await manager.load_module("dummy_mod")

    assert result is True
    assert "dummy_mod" in default_profiler.stats
    assert "init" in default_profiler.stats["dummy_mod"]

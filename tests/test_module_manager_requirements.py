import sys
import types
import importlib
import pytest

from jarvis.core.module_manager import ModuleManager, JarvisModule


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
async def test_load_module_missing_requirement(monkeypatch):
    mod = types.ModuleType("dummy_missing")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    mod.REQUIRES = ["nonexistent_package_123"]
    sys.modules["jarvis.modules.dummy_missing"] = mod

    manager = ModuleManager(DummyJarvis())
    result = await manager.load_module("dummy_missing")
    assert result is False


@pytest.mark.asyncio
async def test_load_module_with_requirement(monkeypatch):
    def fake_find_spec(name):
        if name == "req_pkg":
            return object()
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    mod = types.ModuleType("dummy_ok")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    mod.REQUIRES = ["req_pkg"]
    sys.modules["jarvis.modules.dummy_ok"] = mod

    manager = ModuleManager(DummyJarvis())
    result = await manager.load_module("dummy_ok")
    assert result is True

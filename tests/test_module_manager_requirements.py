import sys
import types

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
async def test_load_module_missing_requirement_fails(monkeypatch):
    mod = types.ModuleType("req_mod")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    mod.REQUIRES = ["some_nonexistent_package_abcxyz"]
    sys.modules["jarvis.modules.req_mod"] = mod

    manager = ModuleManager(DummyJarvis())
    result = await manager.load_module("req_mod")

    assert result is False
    assert "req_mod" not in manager.modules


@pytest.mark.asyncio
async def test_load_module_with_config_requirements(monkeypatch):
    mod = types.ModuleType("req_mod_ok")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    sys.modules["jarvis.modules.req_mod_ok"] = mod

    manager = ModuleManager(DummyJarvis())
    result = await manager.load_module(
        "req_mod_ok", {"requirements": ["sys"]}
    )

    assert result is True
    assert "req_mod_ok" in manager.modules

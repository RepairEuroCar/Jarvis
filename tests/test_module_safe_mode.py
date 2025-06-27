import logging
import sys
import types

import pytest

from jarvis.core.module_manager import ModuleManager, JarvisModule, ModuleState
from core.flags import default_flag_manager


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
async def test_module_load_safe_mode(monkeypatch, caplog):
    mod = types.ModuleType("dummy_mod")
    mod.__version__ = "1.0.0"
    mod.setup = dummy_setup
    sys.modules["jarvis.modules.dummy_mod"] = mod

    manager = ModuleManager(DummyJarvis())
    default_flag_manager.clear_flag("dummy_mod")
    caplog.set_level(logging.ERROR)

    result = await manager.load_module(
        "dummy_mod", {"required_packages": ["nonexistent_lib"]}
    )

    assert result is False
    assert manager.module_states["dummy_mod"] == ModuleState.SAFE_MODE
    assert default_flag_manager.is_flagged("dummy_mod")
    assert any("Missing required packages" in r.message for r in caplog.records)

    default_flag_manager.clear_flag("dummy_mod")

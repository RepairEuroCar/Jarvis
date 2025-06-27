import sys
import types

import pytest

from jarvis.core.module_manager import ModuleManager, JarvisModule
from core.flags import default_flag_manager


class DummyJarvis:
    pass


class FailingModule(JarvisModule):
    async def setup(self, jarvis, config):
        return True

    async def cleanup(self):
        raise RuntimeError("boom")


async def failing_setup(jarvis, config):
    mod = FailingModule()
    await mod.setup(jarvis, config)
    return mod


@pytest.mark.asyncio
async def test_fallback_activation():
    mod = types.ModuleType("fail_mod")
    mod.__version__ = "1.0.0"
    mod.setup = failing_setup
    sys.modules["jarvis.modules.fail_mod"] = mod

    manager = ModuleManager(DummyJarvis())
    activated = []

    async def fallback(exc):
        activated.append(str(exc))

    manager.register_fallback("fail_mod", fallback)

    orig_threshold = default_flag_manager.error_threshold
    default_flag_manager.error_threshold = 1
    default_flag_manager.clear_flag("fail_mod")

    result = await manager.load_module("fail_mod")
    assert result

    await manager.unload_module("fail_mod")

    assert default_flag_manager.is_flagged("fail_mod")
    assert activated

    default_flag_manager.error_threshold = orig_threshold
    default_flag_manager.clear_flag("fail_mod")
    del sys.modules["jarvis.modules.fail_mod"]

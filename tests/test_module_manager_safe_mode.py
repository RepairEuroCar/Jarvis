import importlib

import pytest

from core.flags import default_flag_manager
from jarvis.core.module_manager import ModuleManager, ModuleState


class DummyJarvis:
    pass


@pytest.mark.asyncio
async def test_load_module_safe_mode(monkeypatch):
    manager = ModuleManager(DummyJarvis())
    default_flag_manager.clear_flag("dummy_mod")

    called = False

    def fake_import(name):
        nonlocal called
        called = True
        raise AssertionError("import should not be called")

    monkeypatch.setattr(importlib, "import_module", fake_import)

    result = await manager.load_module(
        "dummy_mod", {"required_packages": ["nonexistent_pkg"]}
    )

    assert result is False
    assert manager.module_states["dummy_mod"] is ModuleState.SAFE_MODE
    assert "dummy_mod" not in manager.modules
    assert default_flag_manager.is_flagged("dummy_mod")
    assert not called

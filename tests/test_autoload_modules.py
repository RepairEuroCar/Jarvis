import pytest

from jarvis.core.main import Jarvis, Settings


@pytest.mark.asyncio
async def test_autoload_priority(monkeypatch):
    settings = Settings(autoload_modules={"mod_a": 50, "mod_b": 10, "mod_c": 30})
    jarvis = Jarvis(settings=settings)

    loaded = []

    async def fake_load(name: str, config=None):
        loaded.append(name)
        jarvis.module_manager.modules[name] = object()
        return True

    monkeypatch.setattr(jarvis.module_manager, "load_module", fake_load)

    await jarvis.load_configured_modules()

    assert loaded == ["mod_b", "mod_c", "mod_a"]
    assert list(jarvis.module_manager.modules.keys()) == loaded

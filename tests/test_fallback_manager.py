import pytest
from utils.fallback_manager import FallbackManager


@pytest.mark.asyncio
async def test_fallback_executes_registered_fallback():
    manager = FallbackManager()

    async def primary():
        raise RuntimeError("boom")

    async def fallback():
        return "ok"

    manager.register(primary, fallback)
    result = await manager.execute(primary)
    assert result == "ok"


@pytest.mark.asyncio
async def test_fallback_success_skips_fallback():
    manager = FallbackManager()

    async def primary():
        return "success"

    async def fallback():
        return "fail"

    manager.register(primary, fallback)
    result = await manager.execute(primary)
    assert result == "success"

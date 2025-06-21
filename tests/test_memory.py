# -----------------------------
# tests/test_memory.py
# -----------------------------
import time

import pytest

from jarvis.memory.manager import MemoryManager


@pytest.fixture
def temp_memory_file(tmp_path):
    return tmp_path / "memory.json"


@pytest.mark.asyncio
async def test_remember_and_query(temp_memory_file):
    mem = MemoryManager(str(temp_memory_file))
    mem.remember("test.key", {"val": 42}, category="test")
    result = mem.query("test.key")
    assert isinstance(result, dict)
    assert result["value"]["val"] == 42
    assert result["category"] == "test"


@pytest.mark.asyncio
async def test_forget(temp_memory_file):
    mem = MemoryManager(str(temp_memory_file))
    mem.remember("delete.me", "gone")
    assert mem.query("delete.me") is not None
    assert mem.forget("delete.me") is True
    assert mem.query("delete.me") is None


@pytest.mark.asyncio
async def test_save_and_load(temp_memory_file):
    mem = MemoryManager(str(temp_memory_file))
    mem.remember("persist.test", 123)
    mem.save()
    time.sleep(0.1)  # ensure filesystem writes are flushed
    new_mem = MemoryManager(str(temp_memory_file))
    assert new_mem.query("persist.test")["value"] == 123

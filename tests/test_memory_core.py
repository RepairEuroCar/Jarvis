import pytest

from jarvis.memory.core import MemoryCore
from jarvis.memory.knowledge_base import KnowledgeBase


@pytest.mark.asyncio
async def test_memory_core_operations():
    mem = MemoryCore()
    e_id = mem.add_event("start", {"ok": True})
    d_id = mem.add_dialogue("user", "hello")
    r_id = mem.add_reasoning("prob", {"answer": 1})

    assert mem.get_event(e_id)["name"] == "start"
    assert mem.get_dialogue(d_id)["text"] == "hello"
    assert mem.get_reasoning(r_id)["solution"]["answer"] == 1

    mem.update_event(e_id, {"ok": False})
    mem.update_dialogue(d_id, "hi")
    mem.update_reasoning(r_id, {"answer": 2})

    assert mem.get_event(e_id)["payload"]["ok"] is False
    assert mem.get_dialogue(d_id)["text"] == "hi"
    assert mem.get_reasoning(r_id)["solution"]["answer"] == 2

    mem.delete_event(e_id)
    mem.delete_dialogue(d_id)
    mem.delete_reasoning(r_id)

    assert mem.get_events() == []
    assert mem.get_dialogues() == []
    assert mem.get_reasoning_history() == []


@pytest.mark.asyncio
async def test_knowledge_base_crud(tmp_path):
    kb_file = tmp_path / "kb.json"
    kb = KnowledgeBase(str(kb_file))
    kb.add_fact("sky", "blue")
    assert kb.get_fact("sky") == "blue"

    kb.update_fact("sky", "grey")
    assert kb.get_fact("sky") == "grey"

    kb2 = KnowledgeBase(str(kb_file))
    assert kb2.get_fact("sky") == "grey"

    kb2.delete_fact("sky")
    assert kb2.get_fact("sky") is None

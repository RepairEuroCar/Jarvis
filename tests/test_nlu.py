# -----------------------------
# tests/test_nlu.py
# -----------------------------
import pytest
from jarvis.nlp.processor import NLUProcessor, TaskSemantics
from jarvis.memory.manager import MemoryManager


@pytest.fixture
def nlu():
    return NLUProcessor()


@pytest.mark.asyncio
async def test_reason_intent(nlu):
    text = "подумай над задачей по логике"
    result = await nlu.process(text)
    assert result["intent"] == "reason_about_problem"
    assert result["confidence"] >= 0.9
    assert "problem_description_entity" in result["entities"]


@pytest.mark.asyncio
async def test_exit_intent(nlu):
    for variant in ["выйти", "exit", "quit"]:
        result = await nlu.process(variant)
        assert result["intent"] == "exit"
        assert result["entities"] == {"raw_args": ""}


@pytest.mark.asyncio
async def test_unknown_command(nlu):
    result = await nlu.process("какая-то неизвестная команда")
    assert result["intent"] == "какая-то"
    assert result["confidence"] < 0.5


@pytest.mark.asyncio
async def test_semantics_translation(nlu):
    result = await nlu.process("переведи это")
    assert result["semantics"] == TaskSemantics.TRANSLATION


@pytest.mark.asyncio
async def test_explain_solution_intent(nlu):
    result = await nlu.process("как ты решил это")
    assert result["intent"] == "explain_solution"


@pytest.mark.asyncio
async def test_custom_pattern_persistence(tmp_path):
    mem_file = tmp_path / "mem.json"
    mem = MemoryManager(str(mem_file))
    nlu = NLUProcessor(memory_manager=mem)
    nlu.add_pattern("greet", "hi", persist=True)
    mem.save()

    mem2 = MemoryManager(str(mem_file))
    nlu2 = NLUProcessor(memory_manager=mem2)
    result = await nlu2.process("hi")
    assert result["intent"] == "greet"

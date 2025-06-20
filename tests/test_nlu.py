# -----------------------------
# tests/test_nlu.py
# -----------------------------
import pytest

from jarvis.memory.manager import MemoryManager
from jarvis.nlp.processor import (
    NLUProcessor,
    TaskSemantics,
    CommandPattern,
    EntityExtractionMode,
)


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


@pytest.mark.asyncio
async def test_learn_correction(tmp_path):
    mem_file = tmp_path / "mem.json"
    mem = MemoryManager(str(mem_file))
    nlu = NLUProcessor(memory_manager=mem)
    nlu.learn_correction("helo", "exit", persist=True)
    mem.save()

    nlu2 = NLUProcessor(memory_manager=MemoryManager(str(mem_file)))
    result = await nlu2.process("helo")
    assert result["intent"] == "exit"


@pytest.mark.asyncio
async def test_intent_model_prediction(monkeypatch):
    calls = {}

    def fake_init(self, model_path):
        calls["init"] = model_path

    def fake_predict(self, text, context=None):
        calls["predict"] = (text, context)
        return {"intent": "greet", "confidence": 0.95}

    monkeypatch.setattr("jarvis.nlp.intent_model.IntentModel.__init__", fake_init)
    monkeypatch.setattr("jarvis.nlp.intent_model.IntentModel.predict", fake_predict)

    nlu = NLUProcessor(model_path="dummy")
    await nlu.process("выйти")
    result = await nlu.process("приветики")

    assert result["intent"] == "greet"
    assert calls["predict"][0] == "приветики"
    assert "exit" in calls["predict"][1]


@pytest.mark.asyncio
async def test_named_entity_extraction(monkeypatch):
    calls = {}

    def fake_init(self, model_name=None):
        calls["ner_init"] = model_name

    def fake_extract(self, text):
        calls["extract"] = text
        return [
            {"text": "Alice", "label": "PERSON"},
            {"text": "Google", "label": "ORG"},
            {"text": "London", "label": "LOC"},
        ]

    monkeypatch.setattr("jarvis.nlp.ner_model.NERModel.__init__", fake_init)
    monkeypatch.setattr("jarvis.nlp.ner_model.NERModel.extract_entities", fake_extract)

    nlu = NLUProcessor(ner_model_name="dummy")
    nlu.command_patterns.insert(
        0,
        CommandPattern(
            intent="who",
            triggers=["show"],
            entity_extraction_mode=EntityExtractionMode.NAMED_ENTITIES,
        ),
    )

    result = await nlu.process("show Alice works at Google in London")

    assert result["intent"] == "who"
    assert calls["extract"] == "Alice works at Google in London"
    assert result["entities"]["PERSON"] == ["Alice"]
    assert result["entities"]["ORG"] == ["Google"]
    assert result["entities"]["LOC"] == ["London"]

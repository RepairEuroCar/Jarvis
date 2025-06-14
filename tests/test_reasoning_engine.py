import logging
from jarvis.reasoning_engine import ReasoningEngine


def test_reasoning_chain_ssh(tmp_path):
    engine = ReasoningEngine()
    result = engine.reason("Найти файл, связанный с SSH", {})
    stages = [s["stage"] for s in result["chain"]]
    assert stages == ["goal", "context", "hypotheses", "plan", "action", "evaluation"]
    assert "~/.ssh" in result["chain"][2]["data"]
    assert isinstance(result["result"], str)


def test_internal_debug_message(caplog):
    engine = ReasoningEngine()
    with caplog.at_level(logging.DEBUG):
        engine.reason("проверить хост", {"unknown_host": True})
    assert any(
        "неизвестный хост" in rec.getMessage() for rec in caplog.records
    )


def test_decision_probability():
    engine = ReasoningEngine()
    prob = engine.decision_probability({"a": 1}, risk=0.2, goal="test", experience=0.5)
    assert 0.0 <= prob <= 1.0

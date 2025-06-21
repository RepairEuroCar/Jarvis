import pytest

from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_handle_command_clarification(monkeypatch):
    jarvis = Jarvis()

    async def fake_process(text: str):
        return {"intent": "help", "confidence": 0.3, "entities": {"raw_args": ""}}

    monkeypatch.setattr(jarvis.nlu, "process", fake_process)

    resp = await jarvis.handle_command("hlep")

    assert "Вы имели в виду" in resp
    assert jarvis.pending_question == "hlep"
    assert jarvis.memory.recall("system.pending_question") == "hlep"

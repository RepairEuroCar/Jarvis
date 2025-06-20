import pytest

from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_handle_command_chain(monkeypatch):
    jarvis = Jarvis()
    calls = []

    async def fake_help(event):
        calls.append(event.text)
        return "ok"

    # replace help command handler
    monkeypatch.setattr(jarvis, "help_command", fake_help)
    jarvis.commands["help"].handler = fake_help

    await jarvis.handle_command("help && help")
    assert calls == ["help", "help"]

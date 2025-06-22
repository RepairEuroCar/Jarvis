import code

from jarvis.core.main import Jarvis, UserEvent


async def test_repl_command(monkeypatch):
    jarvis = Jarvis()
    called = False

    def fake_interact(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(code, "interact", fake_interact)
    event = UserEvent(user_id=0, text="repl")
    result = await jarvis.repl_command(event)
    assert called
    assert "REPL" in result

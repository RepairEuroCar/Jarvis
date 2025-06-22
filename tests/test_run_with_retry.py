import asyncio
import sys

import pytest

from jarvis.core.main import Jarvis, UserEvent


@pytest.mark.asyncio
async def test_run_with_retry_invoked(monkeypatch, tmp_path):
    jarvis = Jarvis()
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"ok", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    script = tmp_path / "hello.py"
    script.write_text("print('hi')", encoding="utf-8")
    event = UserEvent(user_id=0, text=f"run_with_retry {script}")
    result = await jarvis.run_with_retry_command(event)
    assert "ok" in result
    assert called["args"][0] == sys.executable
    assert "scripts/run_with_retry.py" in called["args"]
    assert str(script) in called["args"]
    history = jarvis.memory.recall("commands_history")
    assert history and history[-1]["returncode"] == 0


@pytest.mark.asyncio
async def test_run_with_retry_error(monkeypatch, tmp_path):
    jarvis = Jarvis()

    async def fake_exec(*args, **kwargs):
        class Proc:
            returncode = 1

            async def communicate(self):
                return b"", b"fail"

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    script = tmp_path / "bad.py"
    script.write_text("", encoding="utf-8")
    event = UserEvent(user_id=0, text=f"run_with_retry {script}")
    result = await jarvis.run_with_retry_command(event)
    assert "Error" in result
    history = jarvis.memory.recall("commands_history")
    assert history[-1]["stderr"] == "fail"

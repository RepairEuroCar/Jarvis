import asyncio

import pytest

from modules import kali_tools


@pytest.mark.asyncio
async def test_run_nmap(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"ok", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_nmap("127.0.0.1")
    assert called["args"][0] == "nmap"
    assert "ok" in result


@pytest.mark.asyncio
async def test_bruteforce_ssh(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"done", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt")
    assert "hydra" in called["args"][0]
    assert "done" in result

import asyncio
import io
import sys

import pytest

import cli
from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_cli_list_commands_and_exit(monkeypatch):
    async def fake_init(self):
        pass

    monkeypatch.setattr(Jarvis, "initialize", fake_init)
    stdin = io.StringIO("list_commands\nexit\n")
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)

    await asyncio.wait_for(cli.run(), timeout=2)

    output = stdout.getvalue()
    assert "Jarvis CLI" in output
    assert "list_commands" in output
    assert "Exiting Jarvis" in output


@pytest.mark.asyncio
async def test_cli_invalid_command(monkeypatch):
    async def fake_init(self):
        pass

    monkeypatch.setattr(Jarvis, "initialize", fake_init)
    stdin = io.StringIO("list_commands --bad=1\nexit\n")
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)

    await asyncio.wait_for(cli.run(), timeout=2)

    output = stdout.getvalue()
    assert "Invalid command" in output
    assert "Exiting Jarvis" in output


@pytest.mark.asyncio
async def test_cli_chained_commands(monkeypatch):
    async def fake_init(self):
        pass

    monkeypatch.setattr(Jarvis, "initialize", fake_init)
    stdin = io.StringIO("help && exit\n")
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)

    await asyncio.wait_for(cli.run(), timeout=2)

    output = stdout.getvalue()
    assert "Available commands" in output
    assert output.find("Available commands") < output.find("Exiting Jarvis")

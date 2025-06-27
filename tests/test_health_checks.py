import asyncio
import sys
import types
import pytest

from modules.git_manager import GitManager

# stub sounddevice before importing VoiceInterface
sd_stub = types.SimpleNamespace(query_devices=lambda: [{}])
sys.modules.setdefault("sounddevice", sd_stub)
from modules.voice_interface.interface import VoiceInterface, VoiceConfig


@pytest.mark.asyncio
async def test_git_manager_health_check(monkeypatch):
    gm = GitManager()

    class Proc:
        returncode = 0
        async def communicate(self):
            return b"", b""

    async def fake_exec(*args, **kwargs):
        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    assert await gm.health_check() is True


@pytest.mark.asyncio
async def test_voice_interface_health_check(monkeypatch, tmp_path):
    config = VoiceConfig()
    config.model_path = str(tmp_path)

    class DummyJarvis:
        async def handle_user_input(self, text):
            return None

    vi = VoiceInterface.__new__(VoiceInterface)
    vi.jarvis = DummyJarvis()
    vi.config = config

    monkeypatch.setattr("sounddevice.query_devices", lambda: [{}])
    assert await vi.health_check() is True

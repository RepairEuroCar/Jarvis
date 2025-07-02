import asyncio
import importlib
import logging
from types import SimpleNamespace

import aiohttp
import pytest
import speech_recognition as sr


class DummyResponse:
    def __init__(self, status=200, json_data=None):
        self.status = status
        self._json_data = json_data or {}

    async def __aenter__(self):
        self._start = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        duration = asyncio.get_event_loop().time() - self._start
        logger = get_logger().getChild("http")
        logger.info(
            "%s %s -> %s (%.2fs)",
            self.method,
            self.url,
            self.status,
            duration,
        )
        return False

    async def json(self):
        return self._json_data

    async def text(self):
        return "{}"


class DummySession:
    instances = []

    def __init__(self, *args, **kwargs):
        self.calls = []
        DummySession.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, **kwargs):
        resp = DummyResponse()
        resp.method = "GET"
        resp.url = url
        self.calls.append(("GET", url))
        return resp

    def post(self, url, **kwargs):
        resp = DummyResponse()
        resp.method = "POST"
        resp.url = url
        self.calls.append(("POST", url))
        return resp


from utils.logger import get_logger


@pytest.mark.asyncio
async def test_github_http_logging(monkeypatch, caplog):
    monkeypatch.setattr(aiohttp, "ClientSession", DummySession)
    import utils.http_logging as http_logging

    importlib.reload(http_logging)
    from plugins import github_analyst

    importlib.reload(github_analyst)

    caplog.set_level(logging.INFO)
    url = "https://api.github.com/repos/test/repo/issues/1"
    data, err = await github_analyst._gh_get_json(url, token="t")
    assert err is None
    assert data == {}
    dummy = DummySession.instances[-1]
    assert dummy.calls == [("GET", url)]
    msgs = [r.getMessage() for r in caplog.records]
    assert any("GET" in m and url in m and "-> 200" in m for m in msgs)


class DummyRecognizer:
    def adjust_for_ambient_noise(self, source, duration=1):
        pass

    def listen(self, source, timeout=5):
        return "audio"

    def recognize_google(self, audio, language="en-US"):
        raise sr.RequestError("403 Forbidden")


class DummyMic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


class DummyEngine:
    def __init__(self):
        self.props = {}
        self.voices = [SimpleNamespace(id="dummy", languages=["en_US"])]

    def getProperty(self, name):
        if name == "voices":
            return self.voices
        return self.props.get(name)

    def setProperty(self, name, value):
        self.props[name] = value

    def say(self, text):
        pass

    def runAndWait(self):
        pass

    def stop(self):
        pass


from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_stt_logging_on_error(monkeypatch, caplog):
    monkeypatch.setattr(sr, "Recognizer", lambda: DummyRecognizer())
    monkeypatch.setattr(sr, "Microphone", lambda: DummyMic())
    import pyttsx3

    monkeypatch.setattr(pyttsx3, "init", lambda: DummyEngine())

    jarvis = Jarvis()
    vi = jarvis.voice_interface
    caplog.set_level(logging.INFO)
    await vi.listen()
    msgs = [r.getMessage() for r in caplog.records]
    assert any(
        "HTTP POST https://speech.googleapis.com" in m and "status=403" in m
        for m in msgs
    )

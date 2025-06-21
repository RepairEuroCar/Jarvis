import asyncio

import pyttsx3
import speech_recognition as sr

from jarvis.core.main import Jarvis, UserEvent


class DummyVoice:
    def __init__(self, vid, languages):
        self.id = vid
        self.languages = languages


class DummyEngine:
    def __init__(self):
        self.props = {}
        self.voices = [
            DummyVoice("ru_voice", ["ru_RU"]),
            DummyVoice("en_voice", ["en_US"]),
        ]

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


class DummyRecognizer:
    def adjust_for_ambient_noise(self, source, duration=1):
        pass

    def listen(self, source, timeout=5):
        pass

    def recognize_google(self, audio, language="en-US"):
        return "ok"


class DummyMic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def test_set_language_command(monkeypatch):
    monkeypatch.setattr(pyttsx3, "init", lambda: DummyEngine())
    monkeypatch.setattr(sr, "Recognizer", lambda: DummyRecognizer())
    monkeypatch.setattr(sr, "Microphone", lambda: DummyMic())

    jarvis = Jarvis()
    # initialize voice interface
    _ = jarvis.voice_interface
    engine = jarvis.voice_interface.engine
    assert engine.props.get("voice") == "ru_voice"

    event = UserEvent(user_id=0, text="set_language en-US")
    result = asyncio.run(jarvis.set_language_command(event))

    assert jarvis.settings.recognition_language == "en-US"
    assert jarvis.settings.tts_language == "en-US"
    assert engine.props.get("voice") == "en_voice"
    assert "Language set to en-US" in result

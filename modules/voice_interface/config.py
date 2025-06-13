# 📁 modules/voice_interface/config.py
"""
Конфигурация голосового интерфейса
"""
import os
from typing import List, Optional


class VoiceConfig:
    def __init__(self):
        self.model_path: str = os.path.expanduser(
            "~/.vosk/models/vosk-model-small-ru-0.22"
        )
        self.model_lang: str = "ru"
        self.samplerate: int = 16000
        self.blocksize: int = 4000
        self.device: Optional[int] = None

        self.wake_words: List[str] = ["джарвис", "jarvis", "слушай"]
        self.stop_commands: List[str] = ["стоп", "выход", "молчать"]
        self.enable_wake_word: bool = True

        self.context_phrases: List[str] = [
            "какая погода",
            "включи свет",
            "выключи музыку",
            "добавь задачу",
            "открой настройки",
            "найди информацию о",
            "[unk]",
        ]

        self.enable_advanced_noise_reduction: bool = True
        self.enable_speaker_diarization: bool = False
        self.enable_emotion_recognition: bool = False
        self.min_transcription_confidence: float = 0.7

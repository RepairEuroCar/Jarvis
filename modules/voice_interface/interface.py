# 📁 modules/voice_interface/interface.py
"""
Модернизированный голосовой интерфейс с расширенными возможностями
"""
import asyncio
import json
import os
import threading
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

import sounddevice as sd
import numpy as np
from voice.stub_vosk import KaldiRecognizer, Model

from .config import VoiceConfig
from .audio_processing import AudioProcessor

logger = logging.getLogger(__name__)


class VoiceStatus(Enum):
    """Статусы голосового интерфейса"""
    STOPPED = auto()
    STARTING = auto()
    LISTENING = auto()
    PROCESSING = auto()
    ERROR = auto()


@dataclass
class StatusResponse:
    """Ответ с состоянием системы"""
    status: VoiceStatus
    message: str
    details: Optional[Dict] = None


class VoiceInterface:
    def __init__(self, jarvis_instance, config: VoiceConfig = None):
        self.jarvis = jarvis_instance
        self.config = config or VoiceConfig()
        self.loop = asyncio.get_event_loop()
        self.audio_queue = asyncio.Queue()
        self.command_history = []
        self.status = VoiceStatus.STOPPED
        self._audio_stream = None
        self._audio_processor_task = None
        self._audio_processor = AudioProcessor(self.config)
        self._callbacks: Dict[str, List[Callable]] = {
            'start': [],
            'stop': [],
            'command': [],
            'error': []
        }

        # Инициализация модели распознавания
        self._init_recognition_model()

    def _init_recognition_model(self):
        """Инициализация модели распознавания речи"""
        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"Модель Vosk не найдена: {self.config.model_path}")
        
        self.model = Model(self.config.model_path)
        context_json = json.dumps(self.config.context_phrases, ensure_ascii=False)
        self.recogn
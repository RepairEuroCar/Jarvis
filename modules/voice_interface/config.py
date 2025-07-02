# 📁 modules/voice_interface/config.py
"""
Расширенная конфигурация голосового интерфейса
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class VoiceConfig:
    """Конфигурация голосового интерфейса"""
    model_path: str = os.path.expanduser("~/.vosk/models/vosk-model-small-ru-0.22")
    model_lang: str = "ru"
    samplerate: int = 16000
    blocksize: int = 4000
    device: Optional[int] = None
    timeout: float = 5.0
    max_queue_size: int = 100
    
    # Параметры wake word
    enable_wake_word: bool = True
    wake_words: List[str] = field(default_factory=lambda: ["джарвис", "jarvis", "слушай"])
    wake_word_threshold: float = 0.7
    
    # Команды управления
    stop_commands: List[str] = field(default_factory=lambda: ["стоп", "выход", "молчать"])
    
    # Контекстные фразы для улучшения распознавания
    context_phrases: List[str] = field(default_factory=lambda: [
        "какая погода",
        "включи свет",
        "выключи музыку",
        "добавь задачу",
        "открой настройки",
        "найди информацию о",
        "[unk]",
    ])
    
    # Дополнительные параметры обработки аудио
    enable_noise_reduction: bool = True
    noise_threshold: float = 0.1
    enable_voice_activity_detection: bool = True
    vad_threshold: float = 0.5
    
    # Логирование и отладка
    debug_mode: bool = False
    log_file: Optional[str] = None
    
    def save(self, file_path: str):
        """Сохранение конфигурации в файл"""
        with open(file_path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> 'VoiceConfig':
        """Загрузка конфигурации из файла"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            return cls(**data)
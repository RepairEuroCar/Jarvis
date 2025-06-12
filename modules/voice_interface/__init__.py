# Проект Jarvis: Распределенная структура голосового модуля

# 📁 modules/voice_interface/__init__.py
"""
Инициализирует голосовой модуль и экспортирует ключевые команды
"""
from .interface import VoiceInterface
from .commands import voice_start, voice_stop
from .config import VoiceConfig

commands = {
    "voice_start": voice_start,
    "voice_stop": voice_stop
}
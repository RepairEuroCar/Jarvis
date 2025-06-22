# Проект Jarvis: Распределенная структура голосового модуля

# 📁 modules/voice_interface/__init__.py
"""
Инициализирует голосовой модуль и экспортирует ключевые команды
"""
from .commands import voice_start, voice_stop
<<<<<<< HEAD
=======
from .config import VoiceConfig
from .interface import VoiceInterface
>>>>>>> main

commands = {"voice_start": voice_start, "voice_stop": voice_stop}

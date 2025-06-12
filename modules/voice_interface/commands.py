# 📁 modules/voice_interface/commands.py
"""
Голосовые команды управления: старт/стоп
"""
from .interface import VoiceInterface
from .config import VoiceConfig

async def voice_start(jarvis, args):
    if not hasattr(jarvis, 'voice_interface') or not jarvis.voice_interface:
        jarvis.voice_interface = VoiceInterface(jarvis, VoiceConfig())
    return await jarvis.voice_interface.start()

async def voice_stop(jarvis, args):
    if hasattr(jarvis, 'voice_interface') and jarvis.voice_interface:
        return await jarvis.voice_interface.stop()
    return "⚠️ Голосовой интерфейс не активен"

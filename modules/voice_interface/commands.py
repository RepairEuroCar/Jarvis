# 📁 modules/voice_interface/commands.py
"""
Улучшенный модуль голосовых команд с расширенным функционалом
"""
from dataclasses import asdict
import logging
from typing import Optional

from .config import VoiceConfig
from .interface import VoiceInterface, VoiceStatus
from .utils import save_config, load_config

logger = logging.getLogger(__name__)


async def voice_start(jarvis, args: str = "") -> str:
    """Запуск голосового интерфейса с возможностью конфигурации"""
    try:
        if not hasattr(jarvis, "voice_interface") or not jarvis.voice_interface:
            config = VoiceConfig()
            
            # Парсинг аргументов для конфигурации
            if args:
                config_params = parse_args(args)
                for key, value in config_params.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            jarvis.voice_interface = VoiceInterface(jarvis, config)
            save_config(config, "voice_config.json")
        
        status = await jarvis.voice_interface.start()
        return status.message
    
    except Exception as e:
        logger.error(f"Ошибка запуска голосового интерфейса: {e}")
        return f"⚠️ Ошибка запуска: {str(e)}"


async def voice_stop(jarvis, args: str = "") -> str:
    """Остановка голосового интерфейса"""
    if hasattr(jarvis, "voice_interface") and jarvis.voice_interface:
        status = await jarvis.voice_interface.stop()
        return status.message
    return "⚠️ Голосовой интерфейс не активен"


async def voice_status(jarvis, args: str = "") -> str:
    """Проверка статуса голосового интерфейса"""
    if hasattr(jarvis, "voice_interface") and jarvis.voice_interface:
        status = jarvis.voice_interface.get_status()
        return str(status)
    return "Голосовой интерфейс не инициализирован"


async def voice_config(jarvis, args: str = "") -> str:
    """Изменение конфигурации на лету"""
    if not hasattr(jarvis, "voice_interface") or not jarvis.voice_interface:
        return "Сначала запустите голосовой интерфейс"
    
    try:
        config_params = parse_args(args)
        await jarvis.voice_interface.update_config(config_params)
        return "Конфигурация успешно обновлена"
    except Exception as e:
        return f"Ошибка обновления конфигурации: {str(e)}"


def parse_args(args: str) -> dict:
    """Парсинг строки аргументов в словарь параметров"""
    params = {}
    for item in args.split():
        if '=' in item:
            key, value = item.split('=', 1)
            params[key] = try_convert(value)
    return params


def try_convert(value: str):
    """Попытка преобразования типов"""
    try:
        return eval(value)
    except:
        return value
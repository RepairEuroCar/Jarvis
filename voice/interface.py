import asyncio
import threading
from functools import partial
from typing import Any, Optional

import pyttsx3
import speech_recognition as sr

from utils.logger import get_logger

logger = get_logger().getChild("Voice")


class VoiceInterface:
    def __init__(self, jarvis: Any):
        self.jarvis = jarvis
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
        except Exception as e:  # Missing PyAudio or no device
            logger.error(f"Microphone init failed: {e}")
            self.microphone = None
        try:
            self.engine = pyttsx3.init()
        except Exception as e:
            logger.error(f"TTS engine init failed: {e}")
            self.engine = None
        self.is_active = False

        if self.engine:
            self._configure_voice()
        if self.microphone:
            self._calibrate_microphone()

    def update_language(self):
        """Reconfigure voice with current settings."""
        if self.engine:
            self._configure_voice()

    def _configure_voice(self):
        """Настройка параметров голоса"""
        if not self.engine:
            return
        self.engine.setProperty("rate", self.jarvis.settings.voice_rate)
        self.engine.setProperty("volume", self.jarvis.settings.voice_volume)
        voices = self.engine.getProperty("voices")
        target_lang = self.jarvis.settings.tts_language.lower()
        selected = None
        for v in voices:
            langs = [
                (l.decode() if isinstance(l, bytes) else str(l))
                .lower()
                .replace("_", "-")
                for l in getattr(v, "languages", [])
            ]
            if any(lang.startswith(target_lang) for lang in langs):
                selected = v
                break
        if not selected:
            selected = voices[0]
        logger.info("Selected voice: %s", getattr(selected, "id", "unknown"))
        self.engine.setProperty("voice", selected.id)

    def _calibrate_microphone(self):
        """Калибровка микрофона"""
        if not self.microphone:
            return
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Микрофон откалиброван")

    async def listen(self) -> Optional[str]:
        """Асинхронное распознавание речи"""
        if not self.microphone:
            logger.error("Microphone not available")
            return None
        with self.microphone as source:
            logger.info("Слушаю...")
            try:
                audio = await asyncio.get_event_loop().run_in_executor(
                    None, self.recognizer.listen, source, 5
                )
                func = partial(
                    self.recognizer.recognize_google,
                    audio,
                    language=self.jarvis.settings.recognition_language,
                )
                text = await asyncio.get_event_loop().run_in_executor(None, func)
                logger.info(f"Распознано: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                logger.warning("Таймаут ожидания речи")
            except Exception as e:
                logger.error(f"Ошибка распознавания: {e}")
        return None

    def say(self, text: str):
        """Синхронное воспроизведение речи"""
        if not self.engine:
            logger.info(f"TTS disabled. Would say: {text}")
            return
        logger.info(f"Озвучиваю: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    async def say_async(self, text: str):
        """Асинхронное воспроизведение речи"""
        await asyncio.get_event_loop().run_in_executor(None, self.say, text)

    async def _listen_loop(self):
        """Цикл прослушивания с активацией"""
        self.is_active = True
        while self.is_active:
            text = await self.listen()
            if text and self.jarvis.settings.voice_activation_phrase in text:
                command = text.split(self.jarvis.settings.voice_activation_phrase, 1)[
                    -1
                ].strip()
                await self.jarvis.handle_command(command, is_voice=True)
            await asyncio.sleep(0.1)

    def start(self):
        """Запуск фонового прослушивания"""
        if self.is_active or not self.microphone:
            return
        self._listen_thread = threading.Thread(
            target=lambda: asyncio.run(self._listen_loop()), daemon=True
        )
        self._listen_thread.start()
        logger.info("Голосовой интерфейс запущен")

    def stop(self):
        """Остановка прослушивания"""
        if not self.is_active:
            return
        self.is_active = False
        if hasattr(self, "_listen_thread"):
            self._listen_thread.join(timeout=1.0)
        try:
            if self.engine:
                self.engine.stop()
        except Exception as e:
            logger.warning(f"Ошибка остановки движка: {e}")
        logger.info("Голосовой интерфейс остановлен")

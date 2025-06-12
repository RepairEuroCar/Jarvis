import speech_recognition as sr
import pyttsx3
import asyncio
import logging
import threading
from typing import Any, Optional

logger = logging.getLogger("Jarvis.Voice")

class VoiceInterface:
    def __init__(self, jarvis: Any):
        self.jarvis = jarvis
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.engine = pyttsx3.init()
        self.is_active = False
        
        self._configure_voice()
        self._calibrate_microphone()

    def _configure_voice(self):
        """Настройка параметров голоса"""
        self.engine.setProperty('rate', self.jarvis.settings.voice_rate)
        self.engine.setProperty('volume', self.jarvis.settings.voice_volume)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id)

    def _calibrate_microphone(self):
        """Калибровка микрофона"""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Микрофон откалиброван")

    async def listen(self) -> Optional[str]:
        """Асинхронное распознавание речи"""
        with self.microphone as source:
            logger.info("Слушаю...")
            try:
                audio = await asyncio.get_event_loop().run_in_executor(
                    None, self.recognizer.listen, source, 5
                )
                text = await asyncio.get_event_loop().run_in_executor(
                    None, self.recognizer.recognize_google, audio, {'language': 'ru-RU'}
                )
                logger.info(f"Распознано: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                logger.warning("Таймаут ожидания речи")
            except Exception as e:
                logger.error(f"Ошибка распознавания: {e}")
        return None

    def say(self, text: str):
        """Синхронное воспроизведение речи"""
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
                command = text.split(self.jarvis.settings.voice_activation_phrase, 1)[-1].strip()
                await self.jarvis.handle_command(command, is_voice=True)
            await asyncio.sleep(0.1)

    def start(self):
        """Запуск фонового прослушивания"""
        if self.is_active:
            return
        self._listen_thread = threading.Thread(
            target=lambda: asyncio.run(self._listen_loop()),
            daemon=True
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
            self.engine.stop()
        except Exception as e:
            logger.warning(f"Ошибка остановки движка: {e}")
        logger.info("Голосовой интерфейс остановлен")

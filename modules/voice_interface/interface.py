# 📁 modules/voice_interface/interface.py
"""
Основной класс VoiceInterface: инициализация, прослушка, остановка
"""
REQUIRES = ["sounddevice", "vosk"]

import asyncio
import json
import os
import threading

import sounddevice as sd

from voice.stub_vosk import KaldiRecognizer, Model

from .config import VoiceConfig

# import vosk


class VoiceInterface:
    def __init__(self, jarvis_instance, config: VoiceConfig = None):
        self.jarvis = jarvis_instance
        self.config = config or VoiceConfig()
        self.loop = asyncio.get_event_loop()
        self.audio_queue = asyncio.Queue()

        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"Модель Vosk не найдена: {self.config.model_path}")

        self.model = Model(self.config.model_path)
        context_json = json.dumps(self.config.context_phrases, ensure_ascii=False)
        self.recognizer = KaldiRecognizer(
            self.model, self.config.samplerate, context_json
        )

        self.is_running = False
        self.is_listening_active = not self.config.enable_wake_word
        self._audio_stream_thread = None
        self._audio_processor_task = None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio warning: {status}")
        if self.is_running:
            self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, bytes(indata))

    async def _process_audio_data(self):
        while self.is_running or not self.audio_queue.empty():
            try:
                raw_data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            if self.recognizer.AcceptWaveform(raw_data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip().lower()
                if text:
                    print(f"Vosk: {text}")
                    if self.config.enable_wake_word and not self.is_listening_active:
                        if any(word in text for word in self.config.wake_words):
                            self.is_listening_active = True
                            print("🔓 Wake word activated.")
                            self.recognizer.Reset()
                        continue
                    if text in self.config.stop_commands:
                        print("🛑 Stop command detected.")
                        await self.stop()
                        break
                    if asyncio.iscoroutinefunction(self.jarvis.handle_user_input):
                        await self.jarvis.handle_user_input(text)
                    else:
                        await asyncio.to_thread(self.jarvis.handle_user_input, text)
                    if self.config.enable_wake_word:
                        self.is_listening_active = False
                        self.recognizer.Reset()
            else:
                partial = json.loads(self.recognizer.PartialResult())
                if partial.get("partial"):
                    print("Partial:", partial["partial"], end="\r")
            await asyncio.sleep(0.01)

    async def start(self):
        if self.is_running:
            return "🔊 Голос уже запущен"
        self.is_running = True
        self.is_listening_active = not self.config.enable_wake_word
        self.recognizer.Reset()
        self._audio_processor_task = asyncio.create_task(self._process_audio_data())

        def stream():
            with sd.RawInputStream(
                samplerate=self.config.samplerate,
                blocksize=self.config.blocksize,
                device=self.config.device,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                print("🎤 Слушаю...")
                while self.is_running:
                    sd.sleep(100)

        self._audio_stream_thread = threading.Thread(target=stream, daemon=True)
        self._audio_stream_thread.start()
        return "🎤 Голосовой интерфейс запущен."

    async def stop(self):
        if not self.is_running:
            return "🔇 Уже остановлен"
        self.is_running = False
        if self._audio_stream_thread:
            self._audio_stream_thread.join(timeout=2.0)
        if self._audio_processor_task and not self._audio_processor_task.done():
            self._audio_processor_task.cancel()
            try:
                await self._audio_processor_task
            except asyncio.CancelledError:
                pass
        print("🔇 Голос отключён.")
        return "🔇 Голос отключён."

import logging
import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Callable, Awaitable, Optional, TypeVar
from collections import defaultdict
from pathlib import Path
import yaml
from transitions import Machine
from pydantic import BaseModel, BaseSettings
from jarvis.voice.interface import VoiceInterface
from jarvis.memory.manager import MemoryManager
from jarvis.commands.registry import ALL_COMMANDS, CommandInfo
from jarvis.brain import Brain
from jarvis.nlp.processor import NLUProcessor

logger = logging.getLogger("Jarvis.Core")

class UserEvent(BaseModel):
    user_id: int
    text: str
    is_voice: bool = False

class Settings(BaseSettings):
    """Configuration for the :class:`Jarvis` core.

    Values are populated from environment variables defined in ``.env`` and can
    be overridden by a ``config.yaml`` file. Environment variables use the
    ``JARVIS_`` prefix (e.g. ``JARVIS_LOG_LEVEL``).
    """

    default_user: str = "User"
    log_level: str = "INFO"
    max_cache_size: int = 10
    voice_enabled: bool = True
    voice_activation_phrase: str = "джарвис"
    voice_rate: int = 180
    voice_volume: float = 0.9

    class Config:
        env_file = ".env"
        env_prefix = "JARVIS_"

    @classmethod
    def load(cls, yaml_path: str = "config.yaml") -> "Settings":
        """Load settings optionally overriding values from a YAML file."""
        data = {}
        yaml_file = Path(yaml_path)
        if yaml_file.exists():
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read {yaml_path}: {e}")
        return cls(**data)

@dataclass
class RegisteredCommand:
    info: CommandInfo
    handler: Callable
    is_alias: bool = False

class Jarvis:
    states = ['idle', 'listening', 'processing', 'sleeping']

    def __init__(self, settings: Settings = None, config_path: str = "config/config.yaml"):
        # Load settings from YAML and environment unless explicitly provided
        self.settings = settings or Settings.load(config_path)
        self._setup_logging()
        self._setup_state_machine()
        
        self.commands: Dict[str, RegisteredCommand] = {}
        self._memory = None
        self._voice_interface = None
        self._register_commands()
        self.memory  # initialize memory
        self.nlu = NLUProcessor()
        self.brain = Brain(self)
        
    def _setup_logging(self):
        logging.basicConfig(level=self.settings.log_level)
        
    def _setup_state_machine(self):
        self.machine = Machine(model=self, states=self.states, initial='idle')
        self.machine.add_transition('wake', 'sleeping', 'idle')
        self.machine.add_transition('sleep', '*', 'sleeping')
        self.machine.add_transition('listen', 'idle', 'listening')
        self.machine.add_transition('process', 'listening', 'processing')

    @property
    def memory(self) -> MemoryManager:
        if self._memory is None:
            self._memory = MemoryManager()
        return self._memory

    @property
    def voice_interface(self) -> VoiceInterface:
        if self._voice_interface is None and self.settings.voice_enabled:
            self._voice_interface = VoiceInterface(self)
        return self._voice_interface

    def _register_commands(self):
        for cmd_info in ALL_COMMANDS:
            if not hasattr(self, f"{cmd_info.name}_command"):
                continue
                
            handler = getattr(self, f"{cmd_info.name}_command")
            self.commands[cmd_info.name] = RegisteredCommand(
                info=cmd_info, 
                handler=handler
            )
            for alias in cmd_info.aliases:
                self.commands[alias] = RegisteredCommand(
                    info=cmd_info,
                    handler=handler,
                    is_alias=True
                )

    async def initialize(self):
        """Инициализация голосового интерфейса"""
        if self.voice_interface:
            self.voice_interface.start()

    async def handle_command(self, command_text: str, is_voice: bool = False):
        """Обработка команд с поддержкой голоса"""
        parsed = self.parse_input(command_text)
        if not parsed:
            return await self.unknown_command(command_text, is_voice)
            
        cmd = self.commands.get(parsed['command'])
        if not cmd:
            return await self.unknown_command(command_text, is_voice)
            
        event = UserEvent(
            user_id=0,  # Системный пользователь
            text=command_text,
            is_voice=is_voice
        )
        
        result = await cmd.handler(event)
        
        if is_voice and self.voice_interface:
            await self.voice_interface.say_async(result[:200])  # Ограничение длины ответа
            
        return result

    @lru_cache(maxsize=Settings().max_cache_size)
    def parse_input(self, text: str) -> Dict:
        """Упрощенный парсер команд"""
        text = text.lower().strip()
        for cmd in self.commands.values():
            if text.startswith(cmd.info.name) or any(text.startswith(a) for a in cmd.info.aliases):
                return {
                    'command': cmd.info.name,
                    'args': text[len(cmd.info.name):].strip()
                }
        return None

    async def unknown_command(self, text: str, is_voice: bool):
        response = f"Неизвестная команда: {text}"
        if is_voice and self.voice_interface:
            await self.voice_interface.say_async(response)
        return response

    # Пример команды
    async def help_command(self, event: UserEvent):
        return "Доступные команды: " + ", ".join(cmd.info.name for cmd in self.commands.values())

    async def run(self):
        await self.initialize()
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="Jarvis settings helper")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="print JSON schema of the Settings model",
    )
    args = parser.parse_args()

    if args.schema:
        print(json.dumps(Settings.schema(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(Settings().dict(), indent=2, ensure_ascii=False))

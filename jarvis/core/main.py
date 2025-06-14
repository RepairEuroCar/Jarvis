import argparse
import asyncio
import code
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml
from pydantic import BaseModel, BaseSettings
from transitions import Machine

from jarvis.brain import Brain
from jarvis.commands.registry import ALL_COMMANDS, CommandInfo
from jarvis.goal_manager import GoalManager
from jarvis.memory.manager import MemoryManager
from jarvis.nlp.processor import NLUProcessor
from jarvis.voice.interface import VoiceInterface
from jarvis.event_queue import EventQueue
from jarvis.core.sensor_manager import SensorManager
from utils.linter import AstLinter

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
    allowed_networks: List[str] = ["0.0.0.0/0"]

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
    """Main application orchestrator implemented as a Singleton."""

    states = ["idle", "listening", "processing", "sleeping"]
    _instance: Optional["Jarvis"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, settings: Settings = None, config_path: str = "config/config.yaml"
    ):
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
        self.goals = GoalManager(self)
        self.event_queue = EventQueue()
        self.sensor_manager = SensorManager(self, self.event_queue)
        # Initialize per-instance cache for input parsing
        self._parse_input_cached = lru_cache(maxsize=self.settings.max_cache_size)(
            self._parse_input_uncached
        )

    def _setup_logging(self):
        logging.basicConfig(level=self.settings.log_level)

    def _setup_state_machine(self):
        self.machine = Machine(model=self, states=self.states, initial="idle")
        self.machine.add_transition("wake", "sleeping", "idle")
        self.machine.add_transition("sleep", "*", "sleeping")
        self.machine.add_transition("listen", "idle", "listening")
        self.machine.add_transition("process", "listening", "processing")

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

    @property
    def user_name(self) -> str:
        """Return the configured user name from memory or settings."""
        name = self.memory.recall("user_info.name")
        return name or self.settings.default_user

    def _register_commands(self):
        for cmd_info in ALL_COMMANDS:
            if not hasattr(self, f"{cmd_info.name}_command"):
                continue

            handler = getattr(self, f"{cmd_info.name}_command")
            self.commands[cmd_info.name] = RegisteredCommand(
                info=cmd_info, handler=handler
            )
            for alias in cmd_info.aliases:
                self.commands[alias] = RegisteredCommand(
                    info=cmd_info, handler=handler, is_alias=True
                )

    async def initialize(self):
        """Start subsystems like voice interface and sensors."""
        if self.voice_interface:
            self.voice_interface.start()
        await self.event_queue.start()
        self.event_queue.subscribe("voice_command", self._on_voice_command)
        self.event_queue.subscribe("scheduled_tick", self._on_scheduled_tick)
        await self.sensor_manager.start()

    async def handle_command(self, command_text: str, is_voice: bool = False):
        """Обработка команд с поддержкой голоса"""
        parsed = self.parse_input(command_text)
        if not parsed:
            return await self.unknown_command(command_text, is_voice)

        cmd = self.commands.get(parsed["command"])
        if not cmd:
            return await self.unknown_command(command_text, is_voice)

        event = UserEvent(
            user_id=0, text=command_text, is_voice=is_voice  # Системный пользователь
        )

        result = await cmd.handler(event)

        if is_voice and self.voice_interface:
            await self.voice_interface.say_async(
                result[:200]
            )  # Ограничение длины ответа

        return result

    def parse_input(self, text: str) -> Dict:
        """Упрощенный парсер команд с кэшированием"""
        return self._parse_input_cached(text)

    def _parse_input_uncached(self, text: str) -> Dict:
        text = text.lower().strip()
        for cmd in self.commands.values():
            if text.startswith(cmd.info.name) or any(
                text.startswith(a) for a in cmd.info.aliases
            ):
                return {
                    "command": cmd.info.name,
                    "args": text[len(cmd.info.name) :].strip(),
                }
        return None

    async def unknown_command(self, text: str, is_voice: bool):
        response = f"Неизвестная команда: {text}"
        if is_voice and self.voice_interface:
            await self.voice_interface.say_async(response)
        return response

    async def _on_voice_command(self, text: str) -> None:
        await self.handle_command(text, is_voice=True)

    async def _on_scheduled_tick(self) -> None:
        # Placeholder for future scheduled tasks
        pass

    # Пример команды
    async def help_command(self, event: UserEvent):
        return "Доступные команды: " + ", ".join(
            cmd.info.name for cmd in self.commands.values()
        )

    async def lint_command(self, event: UserEvent):
        """Run AST linter on a path."""
        parts = event.text.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: lint <path> [--max-lines N]"

        parser = argparse.ArgumentParser(prog="lint", add_help=False)
        parser.add_argument("path")
        parser.add_argument("--max-lines", type=int, default=50)
        try:
            opts = parser.parse_args(parts[1].split())
        except SystemExit:
            return "Invalid arguments"

        linter = AstLinter(max_function_lines=opts.max_lines)
        errors = linter.lint_paths([opts.path])
        if not errors:
            return "No lint errors found."
        return "\n".join(f"{e.filepath}:{e.lineno}: {e.message}" for e in errors)

    async def code_tips_command(self, event: UserEvent):
        """Provide code improvement suggestions for the given path."""
        parts = event.text.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: code_tips <path> [--max-lines N]"

        parser = argparse.ArgumentParser(prog="code_tips", add_help=False)
        parser.add_argument("path")
        parser.add_argument("--max-lines", type=int, default=50)
        try:
            opts = parser.parse_args(parts[1].split())
        except SystemExit:
            return "Invalid arguments"

        linter = AstLinter(max_function_lines=opts.max_lines)
        errors = linter.lint_paths([opts.path])
        if not errors:
            return "No suggestions. Code looks good."
        tips = [f"{e.filepath}:{e.lineno} – {e.message}" for e in errors]
        return "\n".join(tips)

    async def self_review_command(self, event: UserEvent):
        """Run self review using recent history."""
        review = self.brain.self_review()
        if not review:
            return "No recent code to review."
        lines: List[str] = []
        for problem, info in review.items():
            lines.append(f"{problem}:")
            for w in info["warnings"]:
                lines.append(f"  - {w}")
        return "\n".join(lines)

    async def rate_solutions_command(self, event: UserEvent):
        """Display ratings for stored solutions."""
        thoughts = self.memory.query("brain.thoughts") or {}
        lines: List[str] = []
        for entry in thoughts.values():
            record = entry.get("value") if isinstance(entry, dict) else entry
            rating = record.get("rating")
            if not rating:
                continue
            problem = record.get("problem", "")[:30]
            brevity = rating.get("brevity", {})
            lines.append(
                f"{problem}: lines={brevity.get('lines', 0)}, "
                f"funcs={brevity.get('functions', 0)}, "
                f"MI={rating.get('readability', 0)}, "
                f"risky={rating.get('safety', 0)}"
            )
        if not lines:
            return "No rated solutions."
        return "\n".join(lines)

    async def repl_command(self, event: UserEvent):
        """Запуск интерактивного Python REPL."""
        banner = "Jarvis Python REPL. Type exit() or Ctrl-D to exit."
        local_ns = {"jarvis": self}
        try:
            await asyncio.to_thread(code.interact, banner=banner, local=local_ns)
        except SystemExit:
            pass
        return "REPL closed."

    async def voice_on_command(self, event: UserEvent):
        """Включить голосовой интерфейс."""
        if not self._voice_interface:
            self._voice_interface = VoiceInterface(self)
        if self._voice_interface.is_active:
            return "Голосовой режим уже активен."
        self._voice_interface.start()
        self.settings.voice_enabled = True
        return "Голосовой режим включён."

    async def voice_off_command(self, event: UserEvent):
        """Выключить голосовой интерфейс."""
        if not self._voice_interface or not self._voice_interface.is_active:
            return "Голосовой режим не активен."
        self._voice_interface.stop()
        self.settings.voice_enabled = False
        return "Голосовой режим выключен."

    async def change_voice_command(self, event: UserEvent):
        """Изменить параметры голоса."""
        parts = event.text.split()
        if len(parts) < 3:
            return "Usage: change_voice <rate> <volume>"
        try:
            rate = int(parts[1])
            volume = float(parts[2])
        except ValueError:
            return "Usage: change_voice <rate> <volume>"
        self.settings.voice_rate = rate
        self.settings.voice_volume = volume
        if self._voice_interface:
            self._voice_interface.engine.setProperty("rate", rate)
            self._voice_interface.engine.setProperty("volume", volume)
        return f"Голос обновлён: скорость {rate}, громкость {volume}"

    async def set_goal_command(self, event: UserEvent):
        """Set a goal and optional motivation."""
        parts = event.text.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: set_goal <goal> [motivation]"
        goal = parts[1]
        motivation = parts[2] if len(parts) > 2 else ""
        self.goals.set_goal(goal, motivation)
        return f"Goal set: {goal}" + (
            f" (motivation: {motivation})" if motivation else ""
        )

    async def execute_goal_command(self, event: UserEvent):
        """Execute the current goal if known."""
        data = self.goals.get_goal()
        if not data:
            return "No goal set."
        goal = str(data.get("goal", "")).lower()
        if "уязвимост" in goal or "vulner" in goal:
            from modules import kali_tools

            result = await kali_tools.run_nmap("127.0.0.1")
            return f"Vulnerability scan completed:\n{result}"
        return f"No automated action for goal: {goal}"

    async def run(self):
        await self.initialize()
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    import json

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

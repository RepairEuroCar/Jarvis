import argparse
import asyncio
import code
import logging
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from pydantic import BaseModel

try:  # pydantic v1 fallback
    from pydantic_settings import BaseSettings
except (
    ModuleNotFoundError
):  # pragma: no cover - for environments without pydantic-settings
    from pydantic import BaseSettings

from transitions import Machine

from jarvis.brain import Brain
from jarvis.commands.registry import ALL_COMMANDS, CommandInfo
from jarvis.core.agent_loop import AgentLoop
from jarvis.core.module_manager import ModuleManager
from jarvis.core.sensor_manager import ScheduledTask, SensorManager
from jarvis.event_queue import EventQueue
from jarvis.goal_manager import GoalManager
from jarvis.memory.manager import MemoryManager
from jarvis.nlp.processor import NLUProcessor
from jarvis.plugins import load_plugins
from jarvis.voice.interface import VoiceInterface
from modules.git_manager import GitManager
from utils.update_checker import check_for_updates
from utils.linter import AstLinter
from utils.logger import get_logger, setup_logging
from core.events import register_event_emitter
from core.module_registry import register_module_supplier
import core.system_initializer  # noqa: F401 - triggers diagnostics startup

logger = get_logger().getChild("Core")


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
    recognition_language: str = "ru-RU"
    tts_language: str = "ru"
    allowed_networks: List[str] = ["0.0.0.0/0"]
    plugin_dir: str = "plugins"
    extra_plugin_dirs: List[str] = ["~/.jarvis/plugins"]
    intent_model_path: str = "models/intent"
    clarify_threshold: float = 0.5

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
                with open(yaml_file, encoding="utf-8") as f:
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
    INIT_ORDER = ["voice_interface", "event_queue", "sensor_manager"]
    INIT_THRESHOLDS = {
        "voice_interface": 2.0,
        "event_queue": 1.0,
        "sensor_manager": 1.0,
    }

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
        self.nlu = NLUProcessor(model_path=self.settings.intent_model_path)
        self.brain = Brain(self)
        self.goals = GoalManager(self)
        self.event_queue = EventQueue()
        self.sensor_manager = SensorManager(self, self.event_queue)
        self.module_manager = ModuleManager(self)
        register_module_supplier(lambda: list(self.module_manager.modules.values()))
        register_event_emitter(
            lambda name, data: asyncio.create_task(self.event_queue.emit(name, data))
        )
        self.agent_loop = None
        self._pending_question: Optional[str] = None
        # Initialize per-instance cache for input parsing
        self._parse_input_cached = lru_cache(maxsize=self.settings.max_cache_size)(
            self._parse_input_uncached
        )
        # Load optional plugins from configured directories
        load_plugins(
            self,
            self.settings.plugin_dir,
            self.settings.extra_plugin_dirs,
        )

    def _setup_logging(self):
        level = getattr(logging, str(self.settings.log_level).upper(), logging.INFO)
        setup_logging(level=level)

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

    @property
    def pending_question(self) -> Optional[str]:
        """Return the last question awaiting user clarification."""
        return self._pending_question

    # --------------------------------------------------------------
    # Module management helpers
    # --------------------------------------------------------------

    async def load_module(self, name: str, config: Optional[Dict] = None) -> bool:
        """Load a Jarvis module via :class:`ModuleManager`."""
        return await self.module_manager.load_module(name, config)

    async def unload_module(self, name: str) -> bool:
        """Unload a previously loaded Jarvis module."""
        return await self.module_manager.unload_module(name)

    def register_scheduled_task(
        self, callback: Callable[["Jarvis"], Awaitable[Any]], interval: float
    ) -> None:
        """Register a periodic asynchronous task."""
        self.sensor_manager.register_scheduled_task(callback, interval)

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

    async def _init_step(self, name: str, func: Callable, threshold: float) -> None:
        """Run an initialization step and log its duration."""
        logger.info("Initializing %s...", name)
        start = time.monotonic()
        try:
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
        except Exception as e:  # pragma: no cover - log unexpected errors
            logger.exception("%s initialization failed: %s", name, e)
            raise
        finally:
            duration = time.monotonic() - start
            logger.info("%s initialized in %.2fs", name, duration)
            if duration > threshold:
                logger.warning(
                    "%s initialization took %.2fs which exceeds %.2fs",
                    name,
                    duration,
                    threshold,
                )

    async def initialize(self):
        """Start subsystems like voice interface and sensors with timing."""
        steps = []
        if self.voice_interface:
            steps.append(("voice_interface", self.voice_interface.start))
        steps.append(("event_queue", self.event_queue.start))
        steps.append(("sensor_manager", self.sensor_manager.start))

        for name in self.INIT_ORDER:
            for step_name, func in steps:
                if step_name != name:
                    continue
                await self._init_step(
                    name,
                    func,
                    self.INIT_THRESHOLDS.get(name, 1.0),
                )
                if name == "event_queue":
                    self.event_queue.subscribe("voice_command", self._on_voice_command)
                    self.event_queue.subscribe("scheduled_tick", self._on_scheduled_tick)
                break

    async def handle_command(self, command_text: str, is_voice: bool = False):
        """Обработка команд с поддержкой голоса"""
        if "&&" in command_text:
            results = []
            for part in [p.strip() for p in command_text.split("&&") if p.strip()]:
                results.append(await self.handle_command(part, is_voice))
            return results[-1] if results else None

        nlu_result = await self.nlu.process(command_text)
        if nlu_result.get("confidence", 0.0) < self.settings.clarify_threshold:
            parsed = self.parse_input(command_text)
            if not parsed:
                self._pending_question = command_text
                await self.memory.remember(
                    "system.pending_question", command_text, category="system"
                )
                clarification = f"Вы имели в виду '{nlu_result.get('intent')}'?"
                if is_voice and self.voice_interface:
                    await self.voice_interface.say_async(clarification)
                return clarification

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

    async def _on_scheduled_tick(self, task: ScheduledTask) -> None:
        """Execute registered scheduled tasks."""
        try:
            await task.callback(self)
        except Exception as e:  # pragma: no cover - log and continue
            logger.exception("Scheduled task failed: %s", e)

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
        parser.add_argument("--max-lines", type=int)
        parser.add_argument(
            "--policy",
            type=str,
            default="train/coding_policy.yaml",
            help="Path to coding policy file",
        )
        try:
            opts = parser.parse_args(parts[1].split())
        except SystemExit:
            return "Invalid arguments"

        linter = AstLinter(max_function_lines=opts.max_lines, policy_path=opts.policy)
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
        parser.add_argument("--max-lines", type=int)
        parser.add_argument(
            "--policy",
            type=str,
            default="train/coding_policy.yaml",
            help="Path to coding policy file",
        )
        try:
            opts = parser.parse_args(parts[1].split())
        except SystemExit:
            return "Invalid arguments"

        linter = AstLinter(max_function_lines=opts.max_lines, policy_path=opts.policy)
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

    async def self_update_command(self, event: UserEvent):
        """Commit or pull Jarvis source using GitManager."""
        import shlex

        parts = shlex.split(event.text)
        if len(parts) < 2:
            return "Usage: self_update <commit|pull> ..."

        action = parts[1]
        gm = GitManager()

        if action == "commit":
            if len(parts) < 3:
                return "Usage: self_update commit <message> [remote branch]"

            message = parts[2]
            push_args = " ".join(parts[3:]) if len(parts) > 3 else ""

            add_res = await gm.add(self)
            commit_res = await gm.commit(self, message)
            result = f"{add_res}\n{commit_res}"

            if push_args:
                push_res = await gm.push(self, push_args)
                result += f"\n{push_res}"

            return result

        if action == "pull":
            remote_branch = " ".join(parts[2:]) if len(parts) > 2 else ""
            return await gm.pull(self, remote_branch)

        return "Usage: self_update <commit|pull> ..."

    async def check_updates_command(self, event: UserEvent):
        """Check for remote updates available via git."""
        parts = event.text.split()
        remote = parts[1] if len(parts) > 1 else "origin"
        branch = parts[2] if len(parts) > 2 else "main"
        repo_path = str(Path(__file__).resolve().parents[2])
        commit = await check_for_updates(repo_path, remote, branch)
        if commit:
            return f"Update available: {commit}"
        return "Jarvis is up to date."

    async def run_with_retry_command(self, event: UserEvent):
        """Run a Python script using scripts/run_with_retry.py."""
        import shlex
        import sys
        import time

        parts = shlex.split(event.text)
        if len(parts) < 2:
            return "Usage: run_with_retry <script.py>"

        script = parts[1]
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "scripts/run_with_retry.py",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode().strip()
            err = stderr.decode().strip()
            rc = proc.returncode
        except FileNotFoundError as e:
            out = ""
            err = str(e)
            rc = 1

        record = {
            "script": script,
            "stdout": out,
            "stderr": err,
            "returncode": rc,
            "timestamp": time.time(),
        }
        history = self.memory.recall("commands_history") or []
        history.append(record)
        await self.memory.remember("commands_history", history, category="system")

        return out if rc == 0 else f"Error: {err}"

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

    async def set_language_command(self, event: UserEvent):
        """Change recognition and synthesis language."""
        parts = event.text.split()
        if len(parts) < 2:
            return "Usage: set_language <code>"
        code = parts[1]
        self.settings.recognition_language = code
        self.settings.tts_language = code
        if self._voice_interface:
            self._voice_interface.update_language()
        return f"Language set to {code}"

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

    async def add_goal_command(self, event: UserEvent):
        """Add a goal with priority and optional deadline/source."""
        parser = argparse.ArgumentParser(prog="add_goal", add_help=False)
        parser.add_argument("priority", type=int)
        parser.add_argument("goal")
        parser.add_argument("--deadline", type=float, default=None)
        parser.add_argument("--source", default="user")
        parser.add_argument("--motivation", default="")

        parts = event.text.split()[1:]
        try:
            opts = parser.parse_args(parts)
        except SystemExit:
            return "Usage: add_goal <priority> <goal> [--deadline TS] [--source SRC] [--motivation TEXT]"

        await self.goals.add_goal(
            opts.goal,
            motivation=opts.motivation,
            priority=opts.priority,
            deadline=opts.deadline,
            source=opts.source,
        )
        return f"Goal added: {opts.goal}"

    async def list_goals_command(self, event: UserEvent):
        """List active goals ordered by priority."""
        goals = self.goals.list_goals()
        if not goals:
            return "No active goals."
        lines = []
        for idx, g in enumerate(goals):
            line = f"{idx}: {g['goal']} (priority {g['priority']})"
            if g.get("deadline"):
                line += f" due {g['deadline']}"
            lines.append(line)
        return "\n".join(lines)

    async def remove_goal_command(self, event: UserEvent):
        """Remove a goal by index."""
        parts = event.text.split()
        if len(parts) != 2:
            return "Usage: remove_goal <index>"
        try:
            idx = int(parts[1])
        except ValueError:
            return "Usage: remove_goal <index>"
        if await self.goals.remove_goal(idx):
            return "Goal removed"
        return "Invalid index"

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
        self.agent_loop = AgentLoop(self)
        await self.agent_loop.run()


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

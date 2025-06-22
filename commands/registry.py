"""Command metadata and registration helpers.

Modules should expose a ``register_commands(dispatcher)`` function that
adds their handlers to a :class:`~command_dispatcher.CommandDispatcher`.
Importing a module should not register commands by itself so applications
can decide when to enable them.

Example::

    from command_dispatcher import default_dispatcher
    from modules import ml_trainer

    ml_trainer.register_commands(default_dispatcher)

"""

from dataclasses import dataclass
from enum import Enum, auto


class CommandCategory(Enum):
    CORE = auto()
    VOICE = auto()
    DEVELOPMENT = auto()
    REASONING = auto()
    UTILITY = auto()


@dataclass
class CommandInfo:
    name: str
    description: str
    category: CommandCategory
    usage: str
    aliases: list[str] = None


CORE_COMMANDS = [
    CommandInfo(
        name="help",
        description="Показывает справку по командам",
        category=CommandCategory.CORE,
        usage="help [команда]",
        aliases=["помощь", "справка"],
    ),
    CommandInfo(
        name="exit",
        description="Завершает работу Jarvis",
        category=CommandCategory.CORE,
        usage="exit",
        aliases=["выход", "завершение"],
    ),
]

VOICE_COMMANDS = [
    CommandInfo(
        name="voice_on",
        description="Включает голосовой режим",
        category=CommandCategory.VOICE,
        usage="voice_on",
        aliases=["включи голос"],
    ),
    CommandInfo(
        name="voice_off",
        description="Выключает голосовой режим",
        category=CommandCategory.VOICE,
        usage="voice_off",
        aliases=["выключи голос"],
    ),
    CommandInfo(
        name="change_voice",
        description="Изменяет параметры голоса",
        category=CommandCategory.VOICE,
        usage="change_voice [скорость] [громкость]",
        aliases=["измени голос"],
    ),
<<<<<<< HEAD
]

ALL_COMMANDS = CORE_COMMANDS + VOICE_COMMANDS
=======
    CommandInfo(
        name="set_language",
        description="Change voice recognition and synthesis language",
        category=CommandCategory.VOICE,
        usage="set_language <code>",
        aliases=[],
    ),
]

DEVEL_COMMANDS = [
    CommandInfo(
        name="lint",
        description="Run AST linter on a file or directory",
        category=CommandCategory.DEVELOPMENT,
        usage="lint <path> [--max-lines N]",
        aliases=[],
    ),
    CommandInfo(
        name="self_review",
        description="Review recent generated code for lint issues",
        category=CommandCategory.DEVELOPMENT,
        usage="self_review",
        aliases=[],
    ),
    CommandInfo(
        name="repl",
        description="Запускает интерактивный Python REPL",
        category=CommandCategory.DEVELOPMENT,
        usage="repl",
        aliases=["python"],
    ),
    CommandInfo(
        name="code_tips",
        description="Provide code improvement suggestions",
        category=CommandCategory.DEVELOPMENT,
        usage="code_tips <path> [--max-lines N]",
        aliases=["tips", "советы"],
    ),
    CommandInfo(
        name="rate_solutions",
        description="Show ratings of stored solutions",
        category=CommandCategory.DEVELOPMENT,
        usage="rate_solutions",
        aliases=[],
    ),
    CommandInfo(
        name="self_update",
        description="Update Jarvis source via Git",
        category=CommandCategory.DEVELOPMENT,
        usage="self_update <commit|pull> ...",
        aliases=[],
    ),
    CommandInfo(
        name="run_with_retry",
        description="Run a script with syntax check and retry",
        category=CommandCategory.DEVELOPMENT,
        usage="run_with_retry <script.py>",
        aliases=[],
    ),
]

UTILITY_COMMANDS = [
    CommandInfo(
        name="set_goal",
        description="Set an active goal with optional motivation",
        category=CommandCategory.UTILITY,
        usage="set_goal <goal> [motivation]",
        aliases=["goal"],
    ),
    CommandInfo(
        name="execute_goal",
        description="Execute actions for the current goal",
        category=CommandCategory.UTILITY,
        usage="execute_goal",
        aliases=["run_goal"],
    ),
    CommandInfo(
        name="add_goal",
        description="Add a goal with priority",
        category=CommandCategory.UTILITY,
        usage="add_goal <priority> <goal> [--deadline TS] [--source SRC] [--motivation TEXT]",
        aliases=[],
    ),
    CommandInfo(
        name="list_goals",
        description="List active goals",
        category=CommandCategory.UTILITY,
        usage="list_goals",
        aliases=[],
    ),
    CommandInfo(
        name="remove_goal",
        description="Remove a goal by index",
        category=CommandCategory.UTILITY,
        usage="remove_goal <index>",
        aliases=[],
    ),
]

ALL_COMMANDS = CORE_COMMANDS + VOICE_COMMANDS + DEVEL_COMMANDS + UTILITY_COMMANDS
>>>>>>> main

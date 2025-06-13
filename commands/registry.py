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
]

ALL_COMMANDS = CORE_COMMANDS + VOICE_COMMANDS + DEVEL_COMMANDS

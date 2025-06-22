import re
from pathlib import Path

from command_dispatcher import CommandDispatcher, default_dispatcher

# Pattern for bullet or numbered list items
BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")

# Common verbs indicating requirements
REQUIREMENT_VERBS = {
    "create",
    "add",
    "implement",
    "remove",
    "delete",
    "update",
    "upgrade",
    "refactor",
    "improve",
    "optimize",
    "fix",
    "write",
    "generate",
    "build",
    "support",
    "enable",
    "setup",
    "split",
    "detect",
    "calculate",
    "provide",
    "develop",
    "design",
}


def analyze_spec(text: str) -> list[str]:
    """Extract individual tasks from requirement *text*.

    The function detects bullet points (``-`` or ``*``), numbered lists
    like ``1.`` or ``1)`` and sentences containing known requirement verbs.
    """
    tasks: list[str] = []

    for line in text.splitlines():
        m = BULLET_RE.match(line)
        if m:
            item = line[m.end() :].strip()
            if item:
                tasks.append(item)
    if tasks:
        return tasks

    sentences = re.split(r"[.!?\n]+", text)
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(v in lower for v in REQUIREMENT_VERBS):
            tasks.append(stripped)
    return tasks


async def task_split(file: str) -> str:
    """Read specification from ``file`` and return numbered subtask list."""
    path = Path(file)
    if not path.exists():
        return f"Spec file not found: {file}"
    text = path.read_text(encoding="utf-8")
    tasks = analyze_spec(text)
    if not tasks:
        return "No tasks detected."
    lines = [f"{i + 1}. {t}" for i, t in enumerate(tasks)]
    return "\n".join(lines)


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    """Register ``task_split`` command with the dispatcher."""
    dispatcher.register_command_handler("task_split", None, task_split)


register_commands(default_dispatcher)

__all__ = ["analyze_spec", "task_split", "register_commands"]

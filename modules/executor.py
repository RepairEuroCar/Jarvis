import asyncio
import re
import sys
from pathlib import Path

from reasoning.tracer import parse_tracebacks, suggest_fixes

from command_dispatcher import CommandDispatcher, default_dispatcher
from utils.linter import AstLinter


async def run(path: str = ".") -> dict[str, dict[str, list[str] | int]]:
    """Run pytest and ruff (or AstLinter) on *path*.

    Parameters
    ----------
    path:
        Directory containing the project to check.

    Returns
    -------
    dict
        Dictionary with test pass/fail counts and lint warnings.
    """

    project = str(Path(path))
    passed = failed = 0

    # -----------------------------
    # Run pytest
    # -----------------------------
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        project,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    output = (out.decode() + err.decode()).strip()

    tracebacks = parse_tracebacks(output)
    failure_details = []
    for tb in tracebacks:
        suggestions = suggest_fixes(tb["error"])
        failure_details.append({"traceback": tb, "suggestions": suggestions})

    m = re.search(r"(\d+)\s+passed", output)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", output)
    if m:
        failed = int(m.group(1))

    # -----------------------------
    # Run ruff or fallback to AstLinter
    # -----------------------------
    lint_messages: list[str] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "ruff",
            "check",
            project,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        ruff_output = out.decode().strip()
        if ruff_output:
            lint_messages.extend(ruff_output.splitlines())
    except FileNotFoundError:
        linter = AstLinter()
        errors = linter.lint_paths([project])
        lint_messages = [f"{e.filepath}:{e.lineno}: {e.message}" for e in errors]

    return {
        "tests": {"passed": passed, "failed": failed},
        "lint": {"warnings": lint_messages},
        "errors": failure_details,
    }


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    """Register ``executor run`` command with ``dispatcher``."""

    dispatcher.register_command_handler("executor", "run", run)


register_commands(default_dispatcher)

__all__ = ["run", "register_commands"]

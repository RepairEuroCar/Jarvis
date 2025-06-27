import asyncio
import re
import sys
from pathlib import Path

from reasoning.tracer import parse_tracebacks, suggest_fixes
import logging

logger = logging.getLogger(__name__)

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage
from utils.linter import AstLinter


@track_usage("executor")
async def review_failures() -> str:
    """Return recent failure tracebacks and suggestions."""
    jarvis = getattr(default_dispatcher, "jarvis", None)
    if not jarvis:
        return "Jarvis instance not available"

    failures = jarvis.memory.recall("tests.last_failures")
    if not failures:
        return "No recorded test failures."

    lines: list[str] = []
    for idx, item in enumerate(failures, 1):
        tb = item.get("traceback", {})
        error = tb.get("error", "")
        lines.append(f"{idx}. {error}")
        for sugg in item.get("suggestions", []):
            lines.append(f"   - {sugg}")

    return "\n".join(lines)


@track_usage("executor")
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

    jarvis = getattr(default_dispatcher, "jarvis", None)
    if jarvis is not None:
        try:
            await jarvis.memory.remember("tests.last_failures", failure_details)
        except Exception:
            pass

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
    """Register ``executor`` commands with ``dispatcher``."""

    dispatcher.register_command_handler("executor", "run", run)
    dispatcher.register_command_handler("executor", "review_failures", review_failures)


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Ensure Python executable is accessible."""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        ok = proc.returncode == 0
        if not ok:
            logger.error("executor health check exit code %s", proc.returncode)
        return ok
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Executor health check failed: %s", exc)
        return False

__all__ = ["run", "review_failures", "register_commands"]

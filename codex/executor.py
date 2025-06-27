"""CodexExecutor wrapper for modules.executor.

Provides async wrappers around :mod:`modules.executor` functions so Codex
tasks can import from :mod:`codex.executor`.
"""

from modules import executor
from command_dispatcher import CommandDispatcher, default_dispatcher


async def run(path: str = ".") -> dict[str, dict[str, list[str] | int]]:
    """Run tests and linting via :func:`modules.executor.run`."""
    return await executor.run(path)


async def review_failures() -> str:
    """Return recent failure tracebacks via :func:`modules.executor.review_failures`."""
    return await executor.review_failures()


def register_commands(
    dispatcher: CommandDispatcher = default_dispatcher,
) -> None:
    """Register executor commands with *dispatcher*."""
    executor.register_commands(dispatcher)


__all__ = ["run", "review_failures", "register_commands"]

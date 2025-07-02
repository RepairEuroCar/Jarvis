"""Module usage statistics tracking and reporting."""

import logging
from typing import Dict

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import get_module_stats

logger = logging.getLogger(__name__)


def _format_stats(stats: Dict) -> str:
    """Format module usage statistics for display."""
    if not stats:
        return "No module usage data."
    
    lines = []
    for name, data in stats.items():
        line = (
            f"{name}: calls={data['calls']}, errors={data['errors']}, "
            f"avg_duration={data['avg_duration']:.4f}s"
        )
        lines.append(line)
    return "\n".join(sorted(lines))


def show_stats() -> str:
    """Return formatted module usage statistics."""
    stats = get_module_stats()
    return _format_stats(stats)


def register_commands(
    dispatcher: CommandDispatcher = default_dispatcher
) -> None:
    """Register usage stats command."""
    dispatcher.register_command_handler("usage", "stats", show_stats)


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Verify access to module usage stats."""
    try:
        _ = get_module_stats()
        return True
    except Exception as exc:
        logger.warning("Module usage health check failed: %s", exc)
        return False


__all__ = ["show_stats", "register_commands"]
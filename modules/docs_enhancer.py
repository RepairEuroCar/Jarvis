"""Documentation enhancement tools."""

import logging

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage
from doc.enhancer import enhance_paths

logger = logging.getLogger(__name__)


@track_usage("docs_enhancer")
async def enhance(path: str = '.') -> str:
    """Enhance docstrings under path."""
    changed = enhance_paths([path])
    if not changed:
        return 'No docstrings updated.'
    return 'Updated:\n' + '\n'.join(changed)


def register_commands(
    dispatcher: CommandDispatcher = default_dispatcher
) -> None:
    """Register docs commands."""
    dispatcher.register_command_handler(
        'docs', 
        'enhance', 
        enhance
    )


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Verify enhancement pipeline works."""
    try:
        enhance_paths([])
        return True
    except Exception as exc:
        logger.warning("Docs enhancer health check failed: %s", exc)
        return False


__all__ = ['enhance', 'register_commands']
from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage

from doc.enhancer import enhance_paths


@track_usage("docs_enhancer")
async def enhance(path: str = '.') -> str:
    """Enhance docstrings under *path*."""
    changed = enhance_paths([path])
    if not changed:
        return 'No docstrings updated.'
    return 'Updated:\n' + '\n'.join(changed)


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    dispatcher.register_command_handler('docs', 'enhance', enhance)


register_commands(default_dispatcher)

__all__ = ['enhance', 'register_commands']

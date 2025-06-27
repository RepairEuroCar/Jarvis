from pathlib import Path
import json

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage
import logging

logger = logging.getLogger(__name__)

@track_usage("ml_tools")
async def create_experiment(name: str, config: str | None = None) -> str:
    """Create an experiment directory with optional JSON config."""
    path = Path(name)
    path.mkdir(parents=True, exist_ok=True)
    if config:
        cfg = json.loads(config) if config.lstrip().startswith("{") else json.load(open(config, "r"))
        with open(path / "config.json", "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    return str(path)


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    dispatcher.register_command_handler("ml", "create_experiment", create_experiment)


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Check basic file system operations for experiments."""
    try:
        tmp = Path(".tmp_ml_tools_check")
        tmp.mkdir(exist_ok=True)
        tmp.rmdir()
        return True
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("ML tools health check failed: %s", exc)
        return False

__all__ = [
    "create_experiment",
    "register_commands",
]

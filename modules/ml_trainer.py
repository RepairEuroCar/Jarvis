"""Machine learning training utilities."""

import json
import logging
import os

from command_dispatcher import CommandDispatcher, default_dispatcher

from .ml_trainer_seq2seq import Seq2SeqTrainer

logger = logging.getLogger(__name__)


class _DummyJarvis:
    """Mock Jarvis instance for standalone training."""
    async def publish_event(self, *_, **__):
        return None


async def train(config: str) -> str:
    """Train a seq2seq model using config."""
    if os.path.isfile(config):
        with open(config, encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = json.loads(config)
        
    trainer = Seq2SeqTrainer(_DummyJarvis(), cfg)
    result = await trainer.train_async()
    return json.dumps(result)


async def evaluate(config: str, checkpoint: str) -> str:
    """Evaluate a model using config and checkpoint."""
    if os.path.isfile(config):
        with open(config, encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = json.loads(config)
        
    trainer = Seq2SeqTrainer(_DummyJarvis(), cfg)
    trainer._load_checkpoint(checkpoint)
    result = await trainer.evaluate_async()
    return json.dumps(result)


def register_commands(
    dispatcher: CommandDispatcher = default_dispatcher
) -> None:
    """Register ml commands."""
    dispatcher.register_command_handler("ml", "train", train)
    dispatcher.register_command_handler("ml", "evaluate", evaluate)


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Verify PyTorch is importable."""
    try:
        import torch  # noqa: F401
        return True
    except Exception as exc:
        logger.warning("ML trainer health check failed: %s", exc)
        return False


__all__ = ["train", "evaluate", "Seq2SeqTrainer", "register_commands"]
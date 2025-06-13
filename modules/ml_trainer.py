import json
import os

from command_dispatcher import default_dispatcher
from .ml_trainer_seq2seq import Seq2SeqTrainer


class _DummyJarvis:
    async def publish_event(self, *_, **__):
        """Stub method used when no Jarvis instance is available."""
        return None


async def train(config: str) -> str:
    """Train a seq2seq model using a JSON config file."""
    if os.path.isfile(config):
        with open(config, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = json.loads(config)
    trainer = Seq2SeqTrainer(_DummyJarvis(), cfg)
    result = await trainer.train_async()
    return json.dumps(result)


async def evaluate(config: str, checkpoint: str) -> str:
    """Evaluate a seq2seq model using config and checkpoint."""
    if os.path.isfile(config):
        with open(config, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = json.loads(config)
    trainer = Seq2SeqTrainer(_DummyJarvis(), cfg)
    trainer._load_checkpoint(checkpoint)
    result = await trainer.evaluate_async()
    return json.dumps(result)


# Register handlers with the global dispatcher on import
default_dispatcher.register_command_handler("ml", "train", train)
default_dispatcher.register_command_handler("ml", "evaluate", evaluate)

__all__ = ["train", "evaluate", "Seq2SeqTrainer"]

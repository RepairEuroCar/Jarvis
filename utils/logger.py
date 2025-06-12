import logging
import sys
from typing import Optional


_LOGGER: Optional[logging.Logger] = None


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the Jarvis logger."""
    global _LOGGER
    logger = logging.getLogger("jarvis")
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    """Return the configured logger instance."""
    return _LOGGER or setup_logging()

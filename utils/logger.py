"""Logger utilities for the Jarvis project.

This module provides ``setup_logging`` to configure a global ``logging``
instance and ``get_logger`` to retrieve it. All modules should use these
helpers instead of creating loggers directly so that log output is
consistently formatted.
"""

import logging
import sys
from typing import Optional

_LOGGER: Optional[logging.Logger] = None


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the Jarvis logger."""
    global _LOGGER
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
    logging.getLogger().setLevel(level)
    logger = logging.getLogger("jarvis")
    logger.setLevel(level)
    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    """Return the configured logger instance."""
    return _LOGGER or setup_logging()

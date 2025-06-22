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
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("jarvis")
<<<<<<< HEAD
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
=======
>>>>>>> main
    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    """Return the configured logger instance."""
    return _LOGGER or setup_logging()

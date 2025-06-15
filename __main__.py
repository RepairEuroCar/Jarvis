# -----------------------------
# jarvis/__main__.py
# -----------------------------
import asyncio
import logging
import sys

from utils.logger import setup_logging

from .cli import run

setup_logging(level=logging.INFO)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nJarvis завершил работу.")
